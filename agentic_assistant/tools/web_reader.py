# tools/webpage_reader.py
"""
Improved web content extraction using Mozilla's Readability.js via Playwright in a separate process.
Includes uBlock Origin integration for ad-free content extraction and better resource management.
"""

import os
import sys
import tempfile
import urllib.request
import json
import shutil
import time
import multiprocessing
from multiprocessing import Process, Queue
import traceback
from .registry import tool
from agentic_assistant.config import HTTP_TIMEOUT, USER_AGENT

# Check if Playwright is installed
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not available. Install with 'pip install playwright' and 'playwright install firefox'")

# uBlock Origin XPI download URL
UBLOCK_ORIGIN_URL = "https://addons.mozilla.org/firefox/downloads/file/4218976/ublock_origin-1.56.0.xpi"

def setup_firefox_with_ublock(temp_dir):
    """Set up Firefox with uBlock Origin"""
    firefox_profile = os.path.join(temp_dir, "firefox_profile")
    os.makedirs(firefox_profile, exist_ok=True)
    
    # Create extensions directory
    extensions_dir = os.path.join(firefox_profile, "extensions")
    os.makedirs(extensions_dir, exist_ok=True)
    
    # Download and install uBlock Origin
    xpi_path = os.path.join(temp_dir, "ublock_origin.xpi")
    try:
        urllib.request.urlretrieve(UBLOCK_ORIGIN_URL, xpi_path)
        shutil.copy(xpi_path, os.path.join(extensions_dir, "uBlock0@raymondhill.net.xpi"))
        print("uBlock Origin extension installed")
    except Exception as e:
        print(f"Warning: Failed to download uBlock Origin: {e}")
    
    return firefox_profile

def extract_content_in_process(url, max_length, result_queue):
    """Run the extraction in a separate process with improved resource management"""
    start_time = time.time()
    temp_dir = None
    page = None
    browser_context = None
    playwright_instance = None
    
    try:
        # Check if Playwright is available
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            result_queue.put({
                "error": "Playwright not available",
                "url": url,
                "elapsed_time": time.time() - start_time
            })
            return
        
        print(f"Starting extraction for: {url}")
        temp_dir = tempfile.mkdtemp(prefix="webpage_reader_")
        firefox_profile = setup_firefox_with_ublock(temp_dir)
        
        # Initialize Playwright resources
        playwright_instance = sync_playwright().start()
        browser_context = playwright_instance.firefox.launch_persistent_context(
            user_data_dir=firefox_profile,
            headless=True
        )
        page = browser_context.new_page()
        
        # Configure page
        page.set_extra_http_headers({"User-Agent": USER_AGENT})
        page.set_default_timeout(HTTP_TIMEOUT * 1000)
        
        # Navigate and wait for content
        print(f"Loading {url}...")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        
        # Extract content
        page.add_script_tag(url="https://unpkg.com/@mozilla/readability@0.4.4/Readability.js")
        result = page.evaluate("""() => {
            try {
                const documentClone = document.cloneNode(true);
                const reader = new Readability(documentClone);
                const article = reader.parse();
                
                if (!article) throw new Error("Failed to parse article");
                
                const links = [];
                document.querySelectorAll('a[href]').forEach((link) => {
                    if (link.textContent.trim() && link.href) {
                        links.push({
                            text: link.textContent.trim(),
                            url: link.href,
                            title: link.title || ''
                        });
                    }
                });
                
                return {
                    title: article.title || document.title,
                    byline: article.byline,
                    siteName: article.siteName,
                    textContent: article.textContent,
                    excerpt: article.excerpt,
                    links: links,
                    success: true
                };
            } catch (e) {
                return { error: e.toString(), success: false };
            }
        }""")
        
        # Check if extraction was successful
        if not result.get("success", False):
            # Try fallback extraction
            fallback_content = page.evaluate("""() => {
                const mainContent = document.querySelector('main') || 
                                    document.querySelector('article') || 
                                    document.querySelector('.content') || 
                                    document.querySelector('#content');
                
                const links = [];
                document.querySelectorAll('a[href]').forEach((link) => {
                    if (link.textContent.trim() && link.href) {
                        links.push({
                            text: link.textContent.trim(),
                            url: link.href,
                            title: link.title || ''
                        });
                    }
                });
                
                return {
                    textContent: (mainContent || document.body).textContent,
                    links: links,
                    success: true
                };
            }""")
            
            text_content = fallback_content.get("textContent", "")
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "...[truncated]"
            
            result_queue.put({
                "title": page.title(),
                "url": url,
                "content": text_content,
                "links": fallback_content.get("links", []),
                "extraction_method": "fallback",
                "elapsed_time": time.time() - start_time
            })
        else:
            # Process the successful result
            text_content = result.get("textContent", "")
            if len(text_content) > max_length:
                text_content = text_content[:max_length] + "...[truncated]"
            
            result_queue.put({
                "title": result.get("title", ""),
                "url": url,
                "byline": result.get("byline", ""),
                "site_name": result.get("siteName", ""),
                "content": text_content,
                "excerpt": result.get("excerpt", ""),
                "links": result.get("links", []),
                "extraction_method": "readability",
                "elapsed_time": time.time() - start_time
            })
    
    except Exception as e:
        print(f"Error in extraction: {str(e)}")
        result_queue.put({
            "error": f"Extraction error: {str(e)}",
            "url": url,
            "elapsed_time": time.time() - start_time
        })
    finally:
        # Clean up Playwright resources
        try:
            if page:
                page.close()
            if browser_context:
                browser_context.close()
            if playwright_instance:
                playwright_instance.stop()
        except Exception as e:
            print(f"Error cleaning up Playwright resources: {str(e)}")
        
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Error cleaning up temp directory: {str(e)}")

def fallback_extraction(url):
    """Simple fallback extraction using requests and BeautifulSoup"""
    start_time = time.time()
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        print(f"Using fallback extraction for {url}")
        
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find main content or use body
        main_content = None
        for selector in ['main', 'article', '.content', '#content', '.post', '.entry']:
            content = soup.select_one(selector)
            if content:
                main_content = content
                break
        main_content = main_content or soup.body
        
        # Extract data
        title = soup.title.text if soup.title else "No title"
        links = [{"text": link.text.strip(), "url": link['href']} 
                 for link in soup.find_all('a', href=True) if link.text.strip()]
        text_content = main_content.get_text(separator='\n', strip=True)
        
        elapsed_time = time.time() - start_time
        return {
            "title": title,
            "url": url,
            "content": text_content[:128000] + ("..." if len(text_content) > 128000 else ""),
            "links": links[:100],  # Limit to 100 links
            "extraction_method": "simple",
            "elapsed_time": elapsed_time,
            "_tool_status": f"✓ webpage_reader: Extracted content using fallback method in {elapsed_time:.2f}s"
        }
    except ImportError:
        return {
            "error": "Fallback extraction requires requests and BeautifulSoup",
            "url": url,
            "elapsed_time": time.time() - start_time,
            "_tool_status": "❌ Error: Fallback extraction requires additional packages"
        }
    except Exception as e:
        return {
            "error": f"Fallback extraction error: {str(e)}",
            "url": url,
            "elapsed_time": time.time() - start_time,
            "_tool_status": f"❌ Error: {str(e)}"
        }

@tool(
    name="webpage_reader",
    description="Extract clean, readable content from webpages with preserved links.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the webpage to extract content from."
            }
        },
        "required": ["url"]
    }
)
def execute(url, max_length=128000):
    """Extract readable content from a webpage using Mozilla's Readability.js with improved resource management"""
    start_time = time.time()
    process = None
    
    # Check if Playwright is available
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available, using fallback extraction")
        return fallback_extraction(url)
    
    print(f"Extracting content from: {url}")
    result_queue = Queue()
    
    try:
        # Create and start extraction process
        process = Process(target=extract_content_in_process, args=(url, max_length, result_queue))
        process.daemon = True
        process.start()
        
        # Wait for process with timeout (45 sec minimum or 3x HTTP_TIMEOUT)
        timeout = max(45, HTTP_TIMEOUT * 3)
        last_progress = start_time
        end_time = start_time + timeout  # Calculate the absolute end time
        
        print(f"Waiting up to {timeout} seconds for extraction...")
        
        # Loop until either we get a result, timeout expires, or process ends
        while process.is_alive() and time.time() < end_time:
            # Show progress periodically
            current_time = time.time()
            if current_time - last_progress >= 5:
                elapsed = current_time - start_time
                print(f"Still extracting... ({elapsed:.1f}s elapsed, timeout in {end_time - current_time:.1f}s)")
                last_progress = current_time
                
            # Check for result
            if not result_queue.empty():
                break
            time.sleep(0.1)
        
        # Handle timeout or get result
        elapsed_time = time.time() - start_time
        
        if process.is_alive() and time.time() >= end_time:
            print(f"Extraction timed out after {elapsed_time:.1f}s (limit: {timeout}s)")
            
            # Try fallback
            try:
                import requests
                print("Trying fallback method")
                result = fallback_extraction(url)
                result["_tool_status"] = f"⚠️ webpage_reader: Extraction timed out after {elapsed_time:.1f}s. {result.get('_tool_status', '')}"
                return result
            except ImportError:
                return {
                    "error": f"Extraction timed out after {elapsed_time:.1f}s",
                    "url": url,
                    "_tool_status": f"⚠️ webpage_reader: Extraction timed out after {elapsed_time:.1f}s"
                }
        
        # Process ended or we have a result
        if not result_queue.empty():
            result = result_queue.get()
            total_time = time.time() - start_time
            
            # Add success status if not an error
            if "error" not in result:
                result["_tool_status"] = f"✓ webpage_reader: Extracted content in {total_time:.2f}s using {result.get('extraction_method', 'unknown')} method"
            else:
                result["_tool_status"] = f"❌ Error: {result.get('error', 'Unknown error')}"
            
            return result
        else:
            # Process ended but no result was produced
            print(f"Process ended after {elapsed_time:.1f}s with no result")
            try:
                import requests
                print("Trying fallback extraction method")
                return fallback_extraction(url)
            except ImportError:
                return {
                    "error": "Extraction ended with no result",
                    "url": url,
                    "_tool_status": "⚠️ webpage_reader: Extraction failed with no result"
                }
    except Exception as e:
        print(f"Error in webpage_reader: {str(e)}")
        return {
            "error": f"Error in webpage_reader: {str(e)}",
            "url": url,
            "_tool_status": f"❌ Error: {str(e)}"
        }
    finally:
        # Ensure process is properly terminated
        if process and process.is_alive():
            try:
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1)
            except Exception as e:
                print(f"Error terminating process: {e}")

# Make sure multiprocessing works correctly on Windows
if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    # Simple test if run directly
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"Testing extraction on: {test_url}")
        result = execute(test_url)
        print(json.dumps(result, indent=2))
    else:
        print("Please provide a URL to test")
