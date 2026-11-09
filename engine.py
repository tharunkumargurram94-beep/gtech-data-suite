import os
import time
from google import genai
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from sqlalchemy import create_engine, inspect

load_dotenv()
console = Console()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
You are an elite Senior Data Engineering Copilot. Your job is to take a user's plain-text data pipeline requirement and a live-extracted database schema context, then write clean, production-ready, highly optimized code.
- Handle edge cases: null values, type casting, nested JSON parsing, and schema drift.
- Include comments explaining key transformation steps.
- Output ONLY the clean code block with a brief explanation.
"""

def fetch_live_schema(connection_string: str, table_name: str) -> str:
    """Connects to any on-prem or Azure database and extracts schema live."""
    try:
        engine = create_engine(connection_string)
        inspector = inspect(engine)
        
        # Handle schema and table name parsing if format is schema.table
        if "." in table_name:
            schema_name, tbl_name = table_name.split(".")
        else:
            schema_name, tbl_name = None, table_name
            
        columns = inspector.get_columns(tbl_name, schema=schema_name)
        
        schema_summary = f"Table: {table_name}\nColumns:\n"
        for col in columns:
            schema_summary += f"- {col['name']} ({col['type']})\n"
            
        return schema_summary
    except Exception as e:
        console.print(f"[red]❌ Error connecting to database: {e}[/red]")
        return f"Table: {table_name} (Metadata fetch failed, write generic schema handling)"

def generate_for_all_frameworks(requirement: str, schema_context: str):
    frameworks = ["PySpark", "Teradata SQL", "Snowflake SQL", "dbt", "Airflow"]
    
    for framework in frameworks:
        console.print(f"\n[bold cyan]⚡ Generating {framework} solution...[/bold cyan]\n")
        
        prompt = f"""
        Target Framework: {framework}
        
        Live Source Schema & Metadata:
        {schema_context}
        
        User Requirement:
        {requirement}
        
        Write the complete code to solve this requirement in {framework}.
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content_stream(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config={
                        'system_instruction': SYSTEM_PROMPT,
                        'temperature': 0.2,
                    }
                )
                
                for chunk in response:
                    print(chunk.text, end="", flush=True)
                print("\n" + "="*50 + "\n")
                break
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    time.sleep(attempt + 2)
                else:
                    break

if __name__ == "__main__":
    console.print("[bold green]🚀 Universal Data Engineering Copilot (Azure + On-Prem Mode)[/bold green]\n")
    
    while True:
        # Example Azure SQL connection string: mssql+pyodbc://user:pass@server.database.windows.net:1433/dbname?driver=ODBC+Driver+18+for+SQL+Server
        conn_str = Prompt.ask("Enter Database Connection String (or type 'manual' to skip)")
        table = Prompt.ask("Enter Table Name to Introspect (e.g., dbo.raw_sales)")
        
        if conn_str.lower() == 'manual':
            schema_context = f"Table: {table} (Manual mode)"
        else:
            console.print("[yellow]🔍 Introspecting live database schema...[/yellow]")
            schema_context = fetch_live_schema(conn_str, table)
            console.print(f"[green]✓ Schema extracted successfully![/green]\n")
            
        requirement = Prompt.ask("What do you want to build or fix?")
        
        generate_for_all_frameworks(requirement, schema_context)
        
        if Prompt.ask("\nRun another scenario?", choices=["y", "n"], default="y") == "n":
            break