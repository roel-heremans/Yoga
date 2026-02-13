#!/usr/bin/env python3
"""
Instagram Content Generator CLI

Main entry point for generating Instagram content.
"""

import click
from pathlib import Path
from src.content_generator import ContentGenerator
from src.brand_extractor import BrandExtractor
from src.pdf_preprocessor import PDFPreprocessor
from src.utils import load_config
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)


@click.group()
def cli():
    """Instagram Content Generator for Real Health Kombucha."""
    pass


@cli.command()
@click.option('--theme', '-t', required=True, help='Theme name (e.g., 04_immune_system, 05_kombucha_benefits)')
@click.option('--type', '-T', type=click.Choice(['feed', 'reel'], case_sensitive=False),
              required=True, help='Content type: feed or reel')
@click.option('--image', '-i', type=click.Path(exists=True), help='Specific image file to use (for feed posts)')
@click.option('--videos', '-v', multiple=True, type=click.Path(exists=True),
              help='Specific video files to use (for reels, can specify multiple)')
@click.option('--music', '-m', type=click.Path(exists=True), help='Background music file for reels')
@click.option('--no-pdf', is_flag=True, help='Skip PDF content extraction')
@click.option('--use-quote', is_flag=True, help='Use a quote from the quotes collection (creates quote card or adds as overlay)')
@click.option('--combined', is_flag=True, help='Create combined reel with video + image + quote + health benefit')
@click.option('--llm-refine', is_flag=True, help='Use LLM to refine health benefit text (makes it more digestible and engaging)')
def generate(theme, type, image, videos, music, no_pdf, use_quote, combined, llm_refine):
    """Generate Instagram content (feed post or reel)."""
    try:
        generator = ContentGenerator()
        
        click.echo(f"{Fore.CYAN}Generating {type} content for theme: {theme}{Style.RESET_ALL}")
        
        if type.lower() == 'feed':
            # Generate feed post
            image_path = Path(image) if image else None
            result = generator.generate_feed_post(
                theme,
                image_path=image_path,
                use_pdf_content=not no_pdf,
                use_quote=use_quote
            )
            
            click.echo(f"{Fore.GREEN}✓ Feed post generated successfully!{Style.RESET_ALL}")
            click.echo(f"  Image: {result['image']}")
            click.echo(f"  Caption: {result['caption']}")
            click.echo(f"  Metadata: {result['metadata']}")
        
        elif type.lower() == 'reel':
            # Generate reel
            video_paths = [Path(v) for v in videos] if videos else None
            music_path = Path(music) if music else None
            image_path = Path(image) if image else None
            
            if combined:
                # Generate combined reel with video + image + quote + health benefit
                image_paths = [image_path] if image_path else None
                result = generator.generate_combined_reel(
                    theme,
                    video_paths=video_paths,
                    image_paths=image_paths,
                    use_quote=True,
                    use_pdf_content=not no_pdf,
                    use_llm_refinement=llm_refine,
                    music_path=music_path
                )
            else:
                # Generate regular reel
                result = generator.generate_reel(
                    theme,
                    video_paths=video_paths,
                    use_pdf_content=not no_pdf,
                    music_path=music_path
                )
            
            click.echo(f"{Fore.GREEN}✓ Reel generated successfully!{Style.RESET_ALL}")
            click.echo(f"  Video: {result['video']}")
            click.echo(f"  Caption: {result['caption']}")
            click.echo(f"  Metadata: {result['metadata']}")
    
    except ValueError as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}", err=True)
        exit(1)


@cli.command()
def themes():
    """List available themes."""
    generator = ContentGenerator()
    themes_list = generator.list_themes()
    
    if not themes_list:
        click.echo(f"{Fore.YELLOW}No themes found. Create theme directories in assets/{Style.RESET_ALL}")
        return
    
    click.echo(f"{Fore.CYAN}Available themes:{Style.RESET_ALL}")
    for theme in themes_list:
        stats = generator.get_theme_stats(theme)
        click.echo(f"  {Fore.GREEN}{theme}{Style.RESET_ALL}")
        click.echo(f"    Images: {stats['images']}, Videos: {stats['videos']}, PDFs: {stats['pdfs']}")


@cli.command()
@click.option('--theme', '-t', help='Show stats for specific theme')
def stats(theme):
    """Show statistics about themes and assets."""
    generator = ContentGenerator()
    
    if theme:
        if theme not in generator.list_themes():
            click.echo(f"{Fore.RED}Theme '{theme}' not found{Style.RESET_ALL}", err=True)
            exit(1)
        
        stats = generator.get_theme_stats(theme)
        click.echo(f"{Fore.CYAN}Stats for '{theme}':{Style.RESET_ALL}")
        click.echo(f"  Images: {stats['images']}")
        click.echo(f"  Videos: {stats['videos']}")
        click.echo(f"  PDFs: {stats['pdfs']}")
    else:
        themes_list = generator.list_themes()
        click.echo(f"{Fore.CYAN}Overall Statistics:{Style.RESET_ALL}")
        
        total_images = 0
        total_videos = 0
        total_pdfs = 0
        
        for theme in themes_list:
            stats = generator.get_theme_stats(theme)
            total_images += stats['images']
            total_videos += stats['videos']
            total_pdfs += stats['pdfs']
        
        click.echo(f"  Themes: {len(themes_list)}")
        click.echo(f"  Total Images: {total_images}")
        click.echo(f"  Total Videos: {total_videos}")
        click.echo(f"  Total PDFs: {total_pdfs}")


@cli.command()
def extract_brand():
    """Extract brand colors and fonts from website."""
    click.echo(f"{Fore.CYAN}Extracting brand information from realhealthkombucha.com...{Style.RESET_ALL}")
    
    extractor = BrandExtractor()
    brand_info = extractor.extract_brand_info()
    
    click.echo(f"{Fore.GREEN}✓ Brand extraction complete!{Style.RESET_ALL}")
    click.echo(f"\n{Fore.CYAN}Extracted Information:{Style.RESET_ALL}")
    click.echo(f"  Name: {brand_info['name']}")
    click.echo(f"  Colors:")
    for key, value in brand_info['colors'].items():
        click.echo(f"    {key}: {value}")
    click.echo(f"  Fonts:")
    click.echo(f"    Heading: {brand_info['fonts']['heading']}")
    click.echo(f"    Body: {brand_info['fonts']['body']}")
    
    # Save to config
    config_path = Path(__file__).parent / 'config' / 'settings.yaml'
    extractor.save_to_config(config_path, brand_info)
    
    click.echo(f"\n{Fore.GREEN}Brand information saved to config/settings.yaml{Style.RESET_ALL}")


@cli.command()
@click.option('--theme', '-t', help='Process specific theme (e.g., 05_kombucha_benefits)')
@click.option('--all', is_flag=True, help='Process all themes (04-07)')
@click.option('--max-pages', default=10, type=int, help='Maximum pages to extract per PDF (default: 10)')
@click.option('--force', is_flag=True, help='Reprocess even if JSON already exists')
def preprocess_pdfs(theme, all, max_pages, force):
    """Preprocess PDFs and save structured data to JSON files."""
    try:
        config = load_config()
        preprocessor = PDFPreprocessor(config=config)
        
        if all:
            click.echo(f"{Fore.CYAN}Preprocessing all themes (04-07)...{Style.RESET_ALL}")
            results = preprocessor.preprocess_all_themes(
                max_pages_per_pdf=max_pages,
                force=force
            )
            
            click.echo(f"\n{Fore.GREEN}✓ Preprocessing complete!{Style.RESET_ALL}")
            successful = sum(1 for r in results.values() if 'error' not in r)
            click.echo(f"  Successfully processed: {successful}/{len(results)} themes")
            
            for theme_name, result in results.items():
                if 'error' in result:
                    click.echo(f"  {Fore.RED}✗ {theme_name}: {result['error']}{Style.RESET_ALL}")
                else:
                    json_path = preprocessor.assets_base_path / theme_name / 'content.json'
                    click.echo(f"  {Fore.GREEN}✓ {theme_name}: {json_path}{Style.RESET_ALL}")
        
        elif theme:
            click.echo(f"{Fore.CYAN}Preprocessing theme: {theme}{Style.RESET_ALL}")
            result = preprocessor.preprocess_theme(
                theme,
                max_pages_per_pdf=max_pages,
                force=force
            )
            
            if result:
                json_path = preprocessor.assets_base_path / theme / 'content.json'
                click.echo(f"\n{Fore.GREEN}✓ Preprocessing complete!{Style.RESET_ALL}")
                click.echo(f"  JSON file: {json_path}")
                click.echo(f"  PDFs processed: {result.get('summary', {}).get('total_pdfs', 0)}")
                click.echo(f"  Key points extracted: {len(result.get('summary', {}).get('combined_key_points', []))}")
            else:
                click.echo(f"{Fore.RED}Error: No PDFs found or processing failed{Style.RESET_ALL}", err=True)
                exit(1)
        else:
            click.echo(f"{Fore.RED}Error: Must specify --theme or --all{Style.RESET_ALL}", err=True)
            click.echo("  Example: python3 main.py preprocess-pdfs --theme 05_kombucha_benefits")
            click.echo("  Example: python3 main.py preprocess-pdfs --all")
            exit(1)
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}", err=True)
        exit(1)


@cli.command()
@click.option('--group', '-g', help='Extract quotes from a specific literature group')
@click.option('--all', is_flag=True, help='Extract quotes from all literature groups')
@click.option('--force', is_flag=True, help='Re-extract even if JSON already exists')
@click.option('--intelligent', is_flag=True, help='Use intelligent agent-based extraction (default: from config)')
@click.option('--simple', is_flag=True, help='Use simple extraction method (overrides intelligent)')
@click.option('--chunk-size', type=int, help='Set chunk size in characters (intelligent mode only)')
@click.option('--max-quotes', type=int, help='Maximum quotes to extract per file')
@click.option('--enable-summary', is_flag=True, help='Include chunk summaries in output (intelligent mode)')
def extract_quotes(group, all, force, intelligent, simple, chunk_size, max_quotes, enable_summary):
    """Extract quotes from literature text files using AI."""
    try:
        from src.literature_extractor import LiteratureExtractor
        
        extractor = LiteratureExtractor()
        
        # Determine extraction method
        use_intelligent = None
        if simple:
            use_intelligent = False
        elif intelligent:
            use_intelligent = True
        
        # Update config if chunk_size or max_quotes provided
        if chunk_size:
            extractor.config.setdefault('quote_extraction', {})['chunk_size'] = chunk_size
        if max_quotes:
            extractor.config.setdefault('quote_extraction', {})['max_total_quotes'] = max_quotes
        
        method_name = "intelligent agent-based" if (use_intelligent or extractor.extraction_method == 'intelligent') else "simple"
        click.echo(f"{Fore.CYAN}Using {method_name} extraction method{Style.RESET_ALL}")
        
        if all:
            click.echo(f"{Fore.CYAN}Extracting quotes from all literature groups...{Style.RESET_ALL}")
            results = extractor.extract_all_groups(force=force, use_intelligent=use_intelligent)
            
            click.echo(f"\n{Fore.GREEN}✓ Extraction complete!{Style.RESET_ALL}")
            successful = sum(1 for r in results.values() if r and 'quotes' in r)
            click.echo(f"  Successfully processed: {successful}/{len(results)} groups")
            
            for group_name, result in results.items():
                if result and 'quotes' in result:
                    quotes_count = len(result['quotes'])
                    extraction_method = result.get('extraction_method', 'simple')
                    quotes_file = Path(extractor.assets_base_path) / '10_knowledge' / group_name / 'quotes.json'
                    click.echo(f"  {Fore.GREEN}✓ {group_name}: {quotes_count} quotes extracted ({extraction_method}){Style.RESET_ALL}")
                    
                    if extraction_method == 'intelligent' and result.get('document_summary'):
                        summary = result['document_summary']
                        click.echo(f"    Chunks: {summary.get('total_chunks', 0)}, Themes: {len(summary.get('main_themes', []))}")
                    
                    click.echo(f"    Saved to: {quotes_file}")
                else:
                    click.echo(f"  {Fore.YELLOW}○ {group_name}: Skipped (already exists or no files found){Style.RESET_ALL}")
        
        elif group:
            click.echo(f"{Fore.CYAN}Extracting quotes from group: {group}{Style.RESET_ALL}")
            result = extractor.extract_from_group(group, force=force, use_intelligent=use_intelligent)
            
            if result and 'quotes' in result:
                quotes_count = len(result['quotes'])
                extraction_method = result.get('extraction_method', 'simple')
                quotes_file = Path(extractor.assets_base_path) / '10_knowledge' / group / 'quotes.json'
                click.echo(f"\n{Fore.GREEN}✓ Extraction complete!{Style.RESET_ALL}")
                click.echo(f"  Method: {extraction_method}")
                click.echo(f"  Extracted {quotes_count} quotes")
                
                if extraction_method == 'intelligent' and result.get('document_summary'):
                    summary = result['document_summary']
                    click.echo(f"  Chunks processed: {summary.get('total_chunks', 0)}")
                    click.echo(f"  Main themes: {', '.join(summary.get('main_themes', [])[:5])}")
                
                click.echo(f"  Saved to: {quotes_file}")
                click.echo(f"\n{Fore.YELLOW}Next step: Review and approve quotes in the JSON file before generating quote cards.{Style.RESET_ALL}")
            else:
                click.echo(f"{Fore.YELLOW}No quotes extracted. Check if files exist or use --force to re-extract.{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.RED}Error: Must specify --group or --all{Style.RESET_ALL}", err=True)
            click.echo("  Example: python3 main.py extract-quotes --group BhagavadGita")
            click.echo("  Example: python3 main.py extract-quotes --all --intelligent")
            click.echo("  Example: python3 main.py extract-quotes --group BhagavadGita --chunk-size 6000 --max-quotes 75")
            exit(1)
    
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}", err=True)
        import traceback
        traceback.print_exc()
        exit(1)


@cli.command()
def config():
    """Show current configuration."""
    config_data = load_config()
    
    click.echo(f"{Fore.CYAN}Current Configuration:{Style.RESET_ALL}")
    click.echo(f"\n{Fore.YELLOW}Brand:{Style.RESET_ALL}")
    brand = config_data.get('brand', {})
    click.echo(f"  Name: {brand.get('name', 'N/A')}")
    click.echo(f"  Website: {brand.get('website', 'N/A')}")
    
    click.echo(f"\n{Fore.YELLOW}Colors:{Style.RESET_ALL}")
    colors = brand.get('colors', {})
    for key, value in colors.items():
        click.echo(f"  {key}: {value}")
    
    click.echo(f"\n{Fore.YELLOW}Fonts:{Style.RESET_ALL}")
    fonts = brand.get('fonts', {})
    click.echo(f"  Heading: {fonts.get('heading', 'N/A')}")
    click.echo(f"  Body: {fonts.get('body', 'N/A')}")
    
    click.echo(f"\n{Fore.YELLOW}AI Settings:{Style.RESET_ALL}")
    ai = config_data.get('ai', {})
    click.echo(f"  Provider: {ai.get('provider', 'N/A')}")
    click.echo(f"  Model: {ai.get('model', 'N/A')}")
    click.echo(f"  Language: {ai.get('language', 'N/A')}")
    
    click.echo(f"\n{Fore.YELLOW}Literature Groups:{Style.RESET_ALL}")
    groups = config_data.get('literature_groups', [])
    for group in groups:
        click.echo(f"  - {group.get('name', 'N/A')}: {group.get('display_name', 'N/A')}")


@cli.command()
@click.option('--feeds', '-f', default=3, type=int, help='Number of feed posts to generate (default: 3)')
@click.option('--reels', '-r', default=3, type=int, help='Number of reels to generate (default: 3)')
@click.option('--themes', '-t', multiple=True, help='Specific themes to use (can specify multiple, otherwise uses all available)')
@click.option('--use-quote', is_flag=True, default=True, help='Use quotes in generated content (default: True)')
@click.option('--llm-refine', is_flag=True, default=True, help='Use LLM refinement for health benefits (default: True)')
@click.option('--music', '-m', type=click.Path(exists=True), help='Specific music file to use for all reels (otherwise random)')
def batch_generate(feeds, reels, themes, use_quote, llm_refine, music):
    """Generate multiple feed posts and reels in one batch."""
    import random
    from pathlib import Path
    
    try:
        generator = ContentGenerator()
        available_themes = generator.list_themes()
        
        if not available_themes:
            click.echo(f"{Fore.RED}No themes found. Create theme directories in assets/{Style.RESET_ALL}", err=True)
            exit(1)
        
        # Filter themes if specified
        if themes:
            themes_to_use = [t for t in themes if t in available_themes]
            if not themes_to_use:
                click.echo(f"{Fore.RED}None of the specified themes were found.{Style.RESET_ALL}", err=True)
                exit(1)
        else:
            themes_to_use = available_themes
        
        # Get available music files
        music_files = []
        music_dir = Path(__file__).parent / 'assets' / '00_music'
        if music_dir.exists():
            music_files = list(music_dir.glob('*.mp3'))
        
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}Batch Content Generation{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Themes: {', '.join(themes_to_use)}{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Feed posts: {feeds}{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Reels: {reels}{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Use quotes: {use_quote}{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}LLM refinement: {llm_refine}{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        results = {
            'feeds': [],
            'reels': []
        }
        
        # Generate feed posts
        if feeds > 0:
            click.echo(f"{Fore.CYAN}Generating {feeds} feed post(s)...{Style.RESET_ALL}")
            for i in range(feeds):
                theme = random.choice(themes_to_use)
                click.echo(f"\n{Fore.YELLOW}[{i+1}/{feeds}] Generating feed post for theme: {theme}{Style.RESET_ALL}")
                
                try:
                    result = generator.generate_feed_post(
                        theme,
                        use_pdf_content=True,
                        use_quote=use_quote
                    )
                    results['feeds'].append({
                        'theme': theme,
                        'result': result,
                        'success': True
                    })
                    click.echo(f"{Fore.GREEN}  ✓ Success!{Style.RESET_ALL}")
                    click.echo(f"  Image: {result['image'].name}")
                except Exception as e:
                    results['feeds'].append({
                        'theme': theme,
                        'error': str(e),
                        'success': False
                    })
                    click.echo(f"{Fore.RED}  ✗ Error: {e}{Style.RESET_ALL}")
        
        # Generate reels
        if reels > 0:
            click.echo(f"\n{Fore.CYAN}Generating {reels} reel(s)...{Style.RESET_ALL}")
            for i in range(reels):
                theme = random.choice(themes_to_use)
                music_path = Path(music) if music else (random.choice(music_files) if music_files else None)
                
                click.echo(f"\n{Fore.YELLOW}[{i+1}/{reels}] Generating reel for theme: {theme}{Style.RESET_ALL}")
                if music_path:
                    click.echo(f"  Music: {music_path.name}")
                
                try:
                    result = generator.generate_combined_reel(
                        theme,
                        video_paths=None,
                        image_paths=None,
                        use_quote=use_quote,
                        use_pdf_content=True,
                        use_llm_refinement=llm_refine,
                        music_path=music_path
                    )
                    results['reels'].append({
                        'theme': theme,
                        'result': result,
                        'success': True
                    })
                    click.echo(f"{Fore.GREEN}  ✓ Success!{Style.RESET_ALL}")
                    click.echo(f"  Video: {result['video'].name}")
                except Exception as e:
                    results['reels'].append({
                        'theme': theme,
                        'error': str(e),
                        'success': False
                    })
                    click.echo(f"{Fore.RED}  ✗ Error: {e}{Style.RESET_ALL}")
        
        # Summary
        click.echo(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}Batch Generation Summary{Style.RESET_ALL}")
        click.echo(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        feeds_success = sum(1 for f in results['feeds'] if f.get('success', False))
        reels_success = sum(1 for r in results['reels'] if r.get('success', False))
        
        click.echo(f"{Fore.GREEN}Feed posts: {feeds_success}/{len(results['feeds'])} successful{Style.RESET_ALL}")
        click.echo(f"{Fore.GREEN}Reels: {reels_success}/{len(results['reels'])} successful{Style.RESET_ALL}")
        
        if feeds_success + reels_success > 0:
            click.echo(f"\n{Fore.CYAN}Generated content saved to:{Style.RESET_ALL}")
            click.echo(f"  Feed posts: output/feed_posts/")
            click.echo(f"  Reels: output/reels/")
        
        if feeds_success < len(results['feeds']) or reels_success < len(results['reels']):
            click.echo(f"\n{Fore.YELLOW}Some items failed. Check errors above.{Style.RESET_ALL}")
            exit(1)
    
    except Exception as e:
        click.echo(f"{Fore.RED}Batch generation failed: {e}{Style.RESET_ALL}", err=True)
        exit(1)


if __name__ == '__main__':
    cli()
