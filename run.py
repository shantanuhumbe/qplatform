import os
import sys
import argparse
import subprocess
from quizapp.config import CFA_MODULES, DEFAULT_PDF_PATH, DEFAULT_OUTPUT_PATH, DEFAULT_PARSE_MODEL, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP
from quizapp.parser import run_pdf_parsing_pipeline
from quizapp.utils.data_manager import load_questions_bank, save_questions_bank, merge_vignettes

def parse_command(args):
    """Executes the PDF parsing pipeline based on CLI arguments."""
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Gemini API Key is required. Set GEMINI_API_KEY environment variable or pass --api-key.", file=sys.stderr)
        sys.exit(1)
        
    pdf_path = args.pdf or DEFAULT_PDF_PATH
    if not os.path.exists(pdf_path):
        print(f"Error: Target PDF not found at {pdf_path}. Please check the path.", file=sys.stderr)
        sys.exit(1)
        
    # Resolve page range and module name
    module_name = "Generic PDF Module"
    start_page = None
    end_page = None
    
    if args.module:
        if args.module in CFA_MODULES:
            module_name, start_page, end_page = CFA_MODULES[args.module]
            print(f"Loading pre-mapped CFA Module {args.module}: '{module_name}' (Pages {start_page} to {end_page})")
        else:
            print(f"Error: Module {args.module} must be between 1 and 30.", file=sys.stderr)
            sys.exit(1)
    elif args.pages:
        try:
            start_page, end_page = map(int, args.pages.split("-"))
            module_name = f"Pages {start_page}-{end_page}"
        except ValueError:
            print("Error: Invalid pages format. Use 'start-end', e.g., '1-20'.", file=sys.stderr)
            sys.exit(1)
    else:
        # Fallback to parsing entire document in chunks
        import pypdf
        try:
            reader = pypdf.PdfReader(pdf_path)
            start_page = 1
            end_page = len(reader.pages)
            module_name = "Entire PDF Document"
            print(f"No pages or module specified. Parsing entire document: Pages {start_page} to {end_page}.")
        except Exception as e:
            print(f"Error reading PDF page counts: {e}", file=sys.stderr)
            sys.exit(1)
            
    # Run parsing pipeline
    try:
        new_vignettes = run_pdf_parsing_pipeline(
            pdf_path=pdf_path,
            start_page=start_page,
            end_page=end_page,
            api_key=api_key,
            model=args.model,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            module_name=module_name
        )
        
        print(f"Parsing complete. Fetched {len(new_vignettes)} vignettes.")
        
        # Merge and save
        existing_vignettes = load_questions_bank(DEFAULT_OUTPUT_PATH)
        merged, added = merge_vignettes(existing_vignettes, new_vignettes)
        save_questions_bank(DEFAULT_OUTPUT_PATH, merged)
        
        print(f"Successfully updated question bank. Added {added} new vignettes. Total vignettes: {len(merged)}")
        
    except Exception as e:
        print(f"Critical error during parsing execution: {e}", file=sys.stderr)
        sys.exit(1)

def web_command(args):
    """Launches the Streamlit quiz application."""
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quizapp", "app.py")
    if not os.path.exists(app_path):
        print(f"Error: Streamlit app entry file not found at {app_path}", file=sys.stderr)
        sys.exit(1)
        
    # Dynamically find the streamlit binary in the virtual environment's bin directory
    python_dir = os.path.dirname(sys.executable)
    streamlit_path = os.path.join(python_dir, "streamlit")
    
    # Fallback to standard command search if not found in python's directory
    if not os.path.exists(streamlit_path):
        streamlit_path = "streamlit"
        
    print(f"Launching Streamlit Application using: {streamlit_path}")
    try:
        # Run streamlit pointing to app/app.py with PYTHONPATH set
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
        cmd = [streamlit_path, "run", app_path]
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\nStopping Streamlit Application.")
    except Exception as e:
        print(f"Failed to start Streamlit: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="QPlatform CFA Quiz App CLI Dispatcher")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run")
    
    # 1. Parsing Command
    parser_parse = subparsers.add_parser("parse", help="Parse PDF vignettes and questions using Gemini API")
    parser_parse.add_argument("--pdf", help="Path to the PDF file")
    parser_parse.add_argument("--module", type=int, help="CFA pre-mapped module index (1 to 30)")
    parser_parse.add_argument("--pages", help="Custom page range to parse (e.g. '1-20')")
    parser_parse.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Number of pages to send in one batch")
    parser_parse.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="Number of overlapping pages between chunks")
    parser_parse.add_argument("--api-key", help="Gemini API Key override")
    parser_parse.add_argument("--model", default=DEFAULT_PARSE_MODEL, help="Gemini model choice")
    
    # 2. Web UI Command
    subparsers.add_parser("web", help="Start the Streamlit Web UI Quiz application")
    
    args = parser.parse_args()
    
    if args.command == "parse":
        parse_command(args)
    elif args.command == "web":
        web_command(args)

if __name__ == "__main__":
    main()
