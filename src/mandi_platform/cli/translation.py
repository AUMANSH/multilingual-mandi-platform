"""
CLI commands for translation service testing and management.
"""

import asyncio
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..translation.config import initialize_nlp_libraries
from ..translation.service import TranslationService
from ..translation.models import LanguageCode

app = typer.Typer(help="Translation service commands")
console = Console()


@app.command()
def status():
    """Check the status of all NLP libraries."""
    console.print("\n[bold blue]Checking NLP Libraries Status...[/bold blue]")
    
    status_info = initialize_nlp_libraries()
    
    # Create status table
    table = Table(title="NLP Libraries Status")
    table.add_column("Library", style="cyan", no_wrap=True)
    table.add_column("Available", style="green")
    table.add_column("Details", style="yellow")
    
    for library, lib_status in status_info.items():
        available = "✅ Yes" if lib_status["available"] else "❌ No"
        
        details = []
        if library == "inltk" and lib_status["available"]:
            models = lib_status.get("models", {})
            working_models = sum(1 for status in models.values() if status)
            details.append(f"Models: {working_models}/{len(models)}")
        
        elif library == "indic_nlp" and lib_status["available"]:
            resources = lib_status.get("resources", False)
            details.append(f"Resources: {'✅' if resources else '❌'}")
        
        elif library == "google_translate" and lib_status["available"]:
            api_working = lib_status.get("api_working", False)
            details.append(f"API: {'✅' if api_working else '❌'}")
        
        table.add_row(library.upper(), available, " | ".join(details))
    
    console.print(table)


@app.command()
def test_detection(text: str = typer.Argument(..., help="Text to detect language for")):
    """Test language detection on given text."""
    async def _test():
        service = TranslationService()
        result = await service.detect_language(text)
        
        panel_content = f"""
[bold]Text:[/bold] {text}
[bold]Detected Language:[/bold] {result.detected_language.value} ({result.detected_language.name})
[bold]Confidence:[/bold] {result.confidence_score:.2f}
[bold]Processing Time:[/bold] {result.processing_time_ms:.2f}ms

[bold]All Candidates:[/bold]
"""
        for lang, score in result.all_candidates.items():
            panel_content += f"  • {lang}: {score:.2f}\n"
        
        console.print(Panel(panel_content, title="Language Detection Result", border_style="green"))
    
    asyncio.run(_test())


@app.command()
def test_translation(
    text: str = typer.Argument(..., help="Text to translate"),
    source: str = typer.Option("en", help="Source language code"),
    target: str = typer.Option("hi", help="Target language code")
):
    """Test translation between languages."""
    async def _test():
        try:
            source_lang = LanguageCode(source)
            target_lang = LanguageCode(target)
        except ValueError:
            console.print(f"[red]Error: Unsupported language code. Supported: {[lang.value for lang in LanguageCode]}[/red]")
            return
        
        service = TranslationService()
        result = await service.translate_text(text, source_lang, target_lang)
        
        panel_content = f"""
[bold]Source Text:[/bold] {text}
[bold]Source Language:[/bold] {source_lang.value} ({source_lang.name})
[bold]Target Language:[/bold] {target_lang.value} ({target_lang.name})
[bold]Translated Text:[/bold] {result.translated_text}
[bold]Confidence:[/bold] {result.confidence_score:.2f}
[bold]Engine Used:[/bold] {result.engine_used.value}
[bold]Cached:[/bold] {'Yes' if result.cached else 'No'}
[bold]Processing Time:[/bold] {result.processing_time_ms:.2f}ms
"""
        
        console.print(Panel(panel_content, title="Translation Result", border_style="blue"))
    
    asyncio.run(_test())


@app.command()
def supported_languages():
    """List all supported languages."""
    table = Table(title="Supported Languages")
    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Script", style="yellow")
    
    from ..translation.config import NLPLibraryConfig
    
    for lang_code in NLPLibraryConfig.get_supported_languages():
        config = NLPLibraryConfig.get_language_config(lang_code)
        table.add_row(lang_code, config["name"], config["script"])
    
    console.print(table)


@app.command()
def benchmark():
    """Run translation benchmarks."""
    async def _benchmark():
        service = TranslationService()
        
        test_cases = [
            ("Hello", LanguageCode.ENGLISH, LanguageCode.HINDI),
            ("Thank you", LanguageCode.ENGLISH, LanguageCode.TAMIL),
            ("Good morning", LanguageCode.ENGLISH, LanguageCode.BENGALI),
            ("How are you?", LanguageCode.ENGLISH, LanguageCode.MARATHI),
            ("Welcome", LanguageCode.ENGLISH, LanguageCode.GUJARATI),
        ]
        
        console.print("\n[bold blue]Running Translation Benchmarks...[/bold blue]")
        
        table = Table(title="Translation Benchmark Results")
        table.add_column("Text", style="cyan")
        table.add_column("From", style="green")
        table.add_column("To", style="green")
        table.add_column("Result", style="yellow")
        table.add_column("Engine", style="magenta")
        table.add_column("Time (ms)", style="red")
        table.add_column("Confidence", style="blue")
        
        for text, source_lang, target_lang in test_cases:
            try:
                result = await service.translate_text(text, source_lang, target_lang)
                table.add_row(
                    text,
                    source_lang.value,
                    target_lang.value,
                    result.translated_text,
                    result.engine_used.value,
                    f"{result.processing_time_ms:.1f}",
                    f"{result.confidence_score:.2f}"
                )
            except Exception as e:
                table.add_row(
                    text,
                    source_lang.value,
                    target_lang.value,
                    f"ERROR: {str(e)[:30]}...",
                    "N/A",
                    "N/A",
                    "0.00"
                )
        
        console.print(table)
    
    asyncio.run(_benchmark())


if __name__ == "__main__":
    app()