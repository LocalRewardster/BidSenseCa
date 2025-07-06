#!/usr/bin/env python3
"""
Script to help find the correct CanadaBuys API endpoint.
"""

import asyncio
import httpx
from loguru import logger
from bs4 import BeautifulSoup
import re
import json


async def analyze_canadabuys_site():
    """Analyze the CanadaBuys site to find API endpoints."""
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        ) as client:
            
            # Try to access the main CanadaBuys site
            urls_to_test = [
                "https://canadabuys.canada.ca/en/tender-opportunities",
                "https://canadabuys.canada.ca/en/tender-opportunities?jurisdiction=BC",
                "https://canadabuys.canada.ca/en/tender-opportunities?status=open&jurisdiction=BC",
                "https://canadabuys.canada.ca/en",
                "https://canadabuys.canada.ca"
            ]
            
            for url in urls_to_test:
                logger.info(f"Testing: {url}")
                try:
                    response = await client.get(url)
                    logger.info(f"  Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        logger.info("  ✅ Site accessible")
                        
                        # Parse HTML to look for API hints
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for script tags that might contain API calls
                        scripts = soup.find_all('script')
                        api_hints = []
                        
                        for script in scripts:
                            script_content = script.get_text()
                            
                            # Look for API-related patterns
                            api_patterns = [
                                r'api[/\w]*',
                                r'fetch\([\'"`][^\'"`]*api[^\'"`]*[\'"`]',
                                r'axios\.get\([\'"`][^\'"`]*api[^\'"`]*[\'"`]',
                                r'\.get\([\'"`][^\'"`]*api[^\'"`]*[\'"`]',
                                r'url[\s]*:[\s]*[\'"`][^\'"`]*api[^\'"`]*[\'"`]',
                                r'endpoint[\s]*:[\s]*[\'"`][^\'"`]*api[^\'"`]*[\'"`]',
                            ]
                            
                            for pattern in api_patterns:
                                matches = re.findall(pattern, script_content, re.IGNORECASE)
                                if matches:
                                    api_hints.extend(matches)
                        
                        if api_hints:
                            logger.info(f"  Found {len(api_hints)} API hints:")
                            for hint in api_hints[:10]:  # Show first 10
                                logger.info(f"    - {hint}")
                        
                        # Look for any JSON-LD structured data
                        json_ld_scripts = soup.find_all('script', type='application/ld+json')
                        if json_ld_scripts:
                            logger.info(f"  Found {len(json_ld_scripts)} JSON-LD scripts")
                        
                        # Look for any data attributes that might indicate API endpoints
                        data_attrs = soup.find_all(attrs={"data-api": True})
                        if data_attrs:
                            logger.info(f"  Found {len(data_attrs)} elements with data-api attributes")
                            for attr in data_attrs[:5]:
                                logger.info(f"    - {attr.get('data-api')}")
                        
                        # Look for any forms that might submit to APIs
                        forms = soup.find_all('form')
                        api_forms = []
                        for form in forms:
                            action = form.get('action', '')
                            if 'api' in action.lower():
                                api_forms.append(action)
                        
                        if api_forms:
                            logger.info(f"  Found {len(api_forms)} forms with API actions:")
                            for form in api_forms:
                                logger.info(f"    - {form}")
                        
                        # Look for any AJAX calls in the HTML
                        ajax_patterns = [
                            r'\.ajax\([^)]*url[\s]*:[\s]*[\'"`]([^\'"`]+)[\'"`]',
                            r'fetch\([\'"`]([^\'"`]+)[\'"`]',
                            r'axios\.get\([\'"`]([^\'"`]+)[\'"`]',
                        ]
                        
                        ajax_urls = []
                        for pattern in ajax_patterns:
                            matches = re.findall(pattern, response.text, re.IGNORECASE)
                            ajax_urls.extend(matches)
                        
                        if ajax_urls:
                            logger.info(f"  Found {len(ajax_urls)} potential AJAX URLs:")
                            for url in ajax_urls[:10]:
                                logger.info(f"    - {url}")
                        
                        break  # Found a working site
                    else:
                        logger.warning(f"  ❌ Site returned {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"  ❌ Error accessing {url}: {e}")
            
            logger.info("\n" + "="*60)
            logger.info("NEXT STEPS:")
            logger.info("1. Open https://canadabuys.canada.ca/en/tender-opportunities in your browser")
            logger.info("2. Open DevTools (F12) and go to Network tab")
            logger.info("3. Filter by 'XHR' or 'Fetch'")
            logger.info("4. Apply filters for 'BC' or 'jurisdiction'")
            logger.info("5. Look for API calls that return JSON with opportunity data")
            logger.info("6. Copy the exact URL from the successful API call")
            logger.info("="*60)
            
    except Exception as e:
        logger.error(f"Error analyzing CanadaBuys site: {e}")


async def test_alternative_approaches():
    """Test alternative approaches to get CanadaBuys data."""
    logger.info("\nTesting alternative approaches...")
    
    # Test if there's a public dataset or RSS feed
    alternative_urls = [
        "https://canadabuys.canada.ca/en/tender-opportunities/rss",
        "https://canadabuys.canada.ca/en/tender-opportunities/feed",
        "https://canadabuys.canada.ca/en/tender-opportunities/xml",
        "https://canadabuys.canada.ca/en/tender-opportunities/json",
        "https://canadabuys.canada.ca/api/public/feed",
        "https://canadabuys.canada.ca/en/api/public/feed",
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in alternative_urls:
            try:
                logger.info(f"Testing: {url}")
                response = await client.get(url)
                logger.info(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    logger.info(f"  Content-Type: {content_type}")
                    
                    if 'json' in content_type:
                        try:
                            data = response.json()
                            logger.info(f"  ✅ JSON response with {len(data) if isinstance(data, (list, dict)) else 'unknown'} items")
                        except:
                            logger.warning("  ❌ Invalid JSON")
                    elif 'xml' in content_type or 'rss' in content_type:
                        logger.info(f"  ✅ XML/RSS response")
                    else:
                        logger.info(f"  ✅ Text response")
                        
            except Exception as e:
                logger.error(f"  ❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(analyze_canadabuys_site())
    asyncio.run(test_alternative_approaches()) 