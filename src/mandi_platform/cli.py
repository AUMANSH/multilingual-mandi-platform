"""
Command-line interface for the Multilingual Mandi Platform.

This module provides CLI commands for development, deployment, and maintenance.
"""

import asyncio
from typing import Optional
import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from .config import settings
from .database import init_database, close_database, get_database_manager
from .redis_client import get_redis_manager, close_redis
from .elasticsearch_client import get_elasticsearch_manager, close_elasticsearch
from .cli.translation import app as translation_app

app = typer.Typer(
    name="mandi-server",
    help="Multilingual Mandi Platform CLI",
    add_completion=False,
)

# Add translation subcommands
app.add_typer(translation_app, name="translation", help="Translation service commands")

console = Console()


@app.command()
def dev(
    host: str = typer.Option(
        settings.host, "--host", "-h", help="Host to bind to"
    ),
    port: int = typer.Option(
        settings.port, "--port", "-p", help="Port to bind to"
    ),
    reload: bool = typer.Option(
        True, "--reload/--no-reload", help="Enable auto-reload"
    ),
    log_level: str = typer.Option(
        "info", "--log-level", help="Log level"
    ),
):
    """Start the development server with auto-reload."""
    console.print("[bold green]Starting Multilingual Mandi Platform (Development)[/bold green]")
    console.print(f"Server will be available at: http://{host}:{port}")
    console.print(f"API documentation: http://{host}:{port}/docs")
    console.print(f"Alternative docs: http://{host}:{port}/redoc")
    
    uvicorn.run(
        "mandi_platform.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        reload_dirs=["src"],
    )


@app.command()
def serve(
    host: str = typer.Option(
        settings.host, "--host", "-h", help="Host to bind to"
    ),
    port: int = typer.Option(
        settings.port, "--port", "-p", help="Port to bind to"
    ),
    workers: int = typer.Option(
        settings.workers, "--workers", "-w", help="Number of worker processes"
    ),
    log_level: str = typer.Option(
        settings.log_level.lower(), "--log-level", help="Log level"
    ),
):
    """Start the production server."""
    console.print("[bold blue]Starting Multilingual Mandi Platform (Production)[/bold blue]")
    
    uvicorn.run(
        "mandi_platform.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        access_log=True,
    )


@app.command()
def init_db():
    """Initialize the database with tables."""
    console.print("[bold yellow]Initializing database...[/bold yellow]")
    
    async def _init():
        try:
            await init_database()
            console.print("[bold green]✓ Database initialized successfully[/bold green]")
        except Exception as e:
            console.print(f"[bold red]✗ Database initialization failed: {e}[/bold red]")
            raise typer.Exit(1)
        finally:
            await close_database()
    
    asyncio.run(_init())


@app.command()
def check_health():
    """Check the health of all system components."""
    console.print("[bold yellow]Checking system health...[/bold yellow]")
    
    async def _check():
        table = Table(title="System Health Check")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="green")
        
        # Check database
        try:
            db_manager = get_database_manager()
            async with db_manager.engine.begin() as conn:
                await conn.execute("SELECT 1")
            table.add_row("Database", "✓ Healthy", f"Connected to {settings.database_url.split('@')[-1]}")
        except Exception as e:
            table.add_row("Database", "✗ Unhealthy", str(e))
        
        # Check Redis
        try:
            redis_manager = get_redis_manager()
            is_connected = await redis_manager.ping()
            if is_connected:
                table.add_row("Redis", "✓ Healthy", f"Connected to {settings.redis_url.split('@')[-1]}")
            else:
                table.add_row("Redis", "✗ Unhealthy", "Ping failed")
        except Exception as e:
            table.add_row("Redis", "✗ Unhealthy", str(e))
        
        # Check Elasticsearch
        try:
            es_manager = get_elasticsearch_manager()
            is_connected = await es_manager.ping()
            if is_connected:
                table.add_row("Elasticsearch", "✓ Healthy", f"Connected to {settings.elasticsearch_url}")
            else:
                table.add_row("Elasticsearch", "✗ Unhealthy", "Ping failed")
        except Exception as e:
            table.add_row("Elasticsearch", "✗ Unhealthy", str(e))
        
        console.print(table)
        
        # Cleanup
        await close_database()
        await close_redis()
        await close_elasticsearch()
    
    asyncio.run(_check())


@app.command()
def config():
    """Display current configuration."""
    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")
    
    # Safe settings to display (no secrets)
    safe_settings = {
        "Debug Mode": settings.debug,
        "Host": settings.host,
        "Port": settings.port,
        "Workers": settings.workers,
        "Log Level": settings.log_level,
        "Supported Languages": ", ".join(settings.supported_languages),
        "CORS Origins": ", ".join(settings.cors_origins),
        "Upload Directory": settings.upload_dir,
        "Max File Size": f"{settings.max_file_size / 1024 / 1024:.1f} MB",
        "Redis Cache TTL": f"{settings.redis_cache_ttl} seconds",
        "Translation Cache TTL": f"{settings.translation_cache_ttl} seconds",
        "Price Cache TTL": f"{settings.price_cache_ttl} seconds",
    }
    
    for key, value in safe_settings.items():
        table.add_row(key, str(value))
    
    console.print(table)


@app.command()
def create_indices():
    """Create Elasticsearch indices for the application."""
    console.print("[bold yellow]Creating Elasticsearch indices...[/bold yellow]")
    
    async def _create():
        try:
            es_manager = get_elasticsearch_manager()
            
            # Product index mapping
            product_mapping = {
                "properties": {
                    "id": {"type": "keyword"},
                    "vendor_id": {"type": "keyword"},
                    "name": {
                        "type": "object",
                        "properties": {
                            "hi": {"type": "text", "analyzer": "standard"},
                            "en": {"type": "text", "analyzer": "english"},
                            "ta": {"type": "text", "analyzer": "standard"},
                            "te": {"type": "text", "analyzer": "standard"},
                            "bn": {"type": "text", "analyzer": "standard"},
                            "mr": {"type": "text", "analyzer": "standard"},
                            "gu": {"type": "text", "analyzer": "standard"},
                            "kn": {"type": "text", "analyzer": "standard"},
                            "ml": {"type": "text", "analyzer": "standard"},
                            "pa": {"type": "text", "analyzer": "standard"},
                        }
                    },
                    "description": {
                        "type": "object",
                        "properties": {
                            "hi": {"type": "text", "analyzer": "standard"},
                            "en": {"type": "text", "analyzer": "english"},
                            "ta": {"type": "text", "analyzer": "standard"},
                            "te": {"type": "text", "analyzer": "standard"},
                            "bn": {"type": "text", "analyzer": "standard"},
                            "mr": {"type": "text", "analyzer": "standard"},
                            "gu": {"type": "text", "analyzer": "standard"},
                            "kn": {"type": "text", "analyzer": "standard"},
                            "ml": {"type": "text", "analyzer": "standard"},
                            "pa": {"type": "text", "analyzer": "standard"},
                        }
                    },
                    "category": {"type": "keyword"},
                    "base_price": {"type": "float"},
                    "unit": {"type": "keyword"},
                    "quality_grade": {"type": "keyword"},
                    "availability": {"type": "keyword"},
                    "location": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "keyword"},
                            "state": {"type": "keyword"},
                            "coordinates": {"type": "geo_point"},
                        }
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
            
            # Create product index
            await es_manager.create_index("products", product_mapping)
            console.print("[bold green]✓ Products index created[/bold green]")
            
            # User index mapping (for search and analytics)
            user_mapping = {
                "properties": {
                    "id": {"type": "keyword"},
                    "phone_number": {"type": "keyword"},
                    "preferred_language": {"type": "keyword"},
                    "location": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "keyword"},
                            "state": {"type": "keyword"},
                            "coordinates": {"type": "geo_point"},
                        }
                    },
                    "user_type": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "last_active": {"type": "date"},
                }
            }
            
            # Create user index
            await es_manager.create_index("users", user_mapping)
            console.print("[bold green]✓ Users index created[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]✗ Failed to create indices: {e}[/bold red]")
            raise typer.Exit(1)
        finally:
            await close_elasticsearch()
    
    asyncio.run(_create())


if __name__ == "__main__":
    app()