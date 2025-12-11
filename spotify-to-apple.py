#!/usr/bin/env python3
import os
import sys
import json
import time
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.webdriver.common.action_chains import ActionChains
except ImportError:
    print("Selenium not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium"])
    print("\nSelenium installed! Please run the script again.")
    sys.exit(0)

# Configuration
APPLE_MUSIC_URL = "https://music.apple.com"
DELAY_BETWEEN_SONGS = 1.5  # seconds between each song - can adjust


def get_exported_files():
    """Find all exported JSON files."""
    export_dir = os.path.join(os.path.dirname(__file__), "exported")
    
    if not os.path.exists(export_dir):
        return []
    
    json_files = [f for f in os.listdir(export_dir) if f.endswith('.json')]
    return sorted(json_files, reverse=True)  # Most recent first


def load_songs_from_json(filepath):
    """Load songs from exported JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('tracks', []), data.get('playlist_name', 'Unknown')


def setup_browser(use_profile=True):
    """Set up Chrome browser with options."""
    options = Options()
    
    if use_profile:
        user_data_dir = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
        
        if os.path.exists(user_data_dir):
            options.add_argument(f'--user-data-dir={user_data_dir}')
            options.add_argument('--profile-directory=Default')
    
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        if use_profile:
            print(f"Could not use Chrome profile: {e}")
            print("Trying without profile (you'll need to log in)...")
            return setup_browser(use_profile=False)
        else:
            raise


def add_song_to_library(driver, apple_url, song_name, artist, index, total):
    """Open an Apple Music link and click Add to Library."""
    
    print(f"[{index}/{total}] {song_name} - {artist}")
    
    try:
        # Go directly to the song URL
        driver.get(apple_url)
        time.sleep(2)  # Wait for page to load
        
        # Try multiple selectors for the Add button
        # Apple Music uses different layouts for songs vs albums
        add_button_selectors = [
            # Song page add button
            "button[data-testid='add-to-library-button']",
            "button[aria-label='Add to Library']",
            "button[aria-label='Add to library']",
            # Generic add buttons
            ".we-button--add",
            "button.add-to-library",
            # Plus icon buttons
            "button[aria-label*='Add']",
            ".commerce-button-add",
            # SVG plus icon in button
            "button svg[aria-label*='add' i]",
        ]
        
        add_button = None
        
        for selector in add_button_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        add_button = el
                        break
                if add_button:
                    break
            except:
                continue
        
        # Also try XPath for text-based search
        if not add_button:
            xpath_selectors = [
                "//button[contains(@aria-label, 'Add')]",
                "//button[contains(text(), 'Add')]",
                "//*[contains(@class, 'add')]//button",
            ]
            for xpath in xpath_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            add_button = el
                            break
                    if add_button:
                        break
                except:
                    continue
        
        if add_button:
            # Scroll button into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", add_button)
            time.sleep(0.3)
            
            # Try clicking
            try:
                add_button.click()
            except:
                # If regular click fails, try JavaScript click
                driver.execute_script("arguments[0].click();", add_button)
            
            print(f"         ✓ Added to library!")
            return True
        else:
            # Check if already in library (checkmark shown instead of +)
            checkmark_selectors = [
                "button[aria-label='In Library']",
                "button[aria-label='Added to Library']",
                ".we-button--added",
            ]
            
            for selector in checkmark_selectors:
                try:
                    if driver.find_elements(By.CSS_SELECTOR, selector):
                        print(f"         ✓ Already in library")
                        return True
                except:
                    pass
            
            print(f"         ⚠ Could not find Add button")
            return False
            
    except Exception as e:
        print(f"         ✗ Error: {str(e)[:50]}")
        return False


def main():
    print("=" * 60)
    print("  Automated Apple Music Library Adder")
    print("=" * 60)
    print()
    print("This will automatically add songs to your Apple Music library.")
    print()
    print("Requirements:")
    print("  ✓ Chrome browser installed")
    print("  ✓ Apple Music subscription")
    print("  ✓ Already ran transfer_to_apple.py")
    print()
    
    # Find exported files
    exported_files = get_exported_files()
    
    if not exported_files:
        print("❌ No exported files found!")
        print("Please run transfer_to_apple.py first to generate a song list.")
        return
    
    # Let user select a file
    print("Available exports:")
    for i, f in enumerate(exported_files, 1):
        print(f"  {i}. {f}")
    
    print()
    choice = input(f"Select file (1-{len(exported_files)}): ").strip()
    
    try:
        file_idx = int(choice) - 1
        if file_idx < 0 or file_idx >= len(exported_files):
            raise ValueError()
        selected_file = exported_files[file_idx]
    except ValueError:
        print("Invalid choice!")
        return
    
    # Load songs
    export_dir = os.path.join(os.path.dirname(__file__), "exported")
    filepath = os.path.join(export_dir, selected_file)
    songs, playlist_name = load_songs_from_json(filepath)
    
    print(f"\nLoaded {len(songs)} songs from '{playlist_name}'")
    
    # Filter to only songs found on Apple Music (have URLs)
    found_songs = [s for s in songs if s.get('found') and s.get('apple_url')]
    print(f"Songs with Apple Music links: {len(found_songs)}")
    
    if not found_songs:
        print("No songs with Apple Music links to add!")
        return
    
    # Ask where to start (in case of resume)
    print()
    start_from = input(f"Start from song number (1-{len(found_songs)}) [1]: ").strip()
    try:
        start_idx = int(start_from) - 1 if start_from else 0
        if start_idx < 0:
            start_idx = 0
        if start_idx >= len(found_songs):
            start_idx = 0
    except:
        start_idx = 0
    
    songs_to_process = found_songs[start_idx:]
    print(f"\nWill add {len(songs_to_process)} songs to Apple Music library.")
    
    # Ask for confirmation
    print()
    print("⚠️  IMPORTANT: Close ALL Chrome windows before continuing!")
    print("   (The script needs exclusive access to Chrome)")
    print()
    confirm = input("Ready to start? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return
    
    # Start browser
    print("\nStarting Chrome browser...")
    
    try:
        driver = setup_browser()
    except Exception as e:
        print(f"\n❌ Could not start Chrome browser.")
        print(f"Error: {e}")
        print("\nMake sure:")
        print("  1. Chrome is installed")
        print("  2. All Chrome windows are closed")
        print("  3. Try running as administrator if needed")
        return
    
    try:
        # Go to Apple Music first
        print("\nOpening Apple Music...")
        driver.get(APPLE_MUSIC_URL)
        time.sleep(2)
        
        print()
        print("=" * 60)
        print("Check the browser window.")
        print("If you need to log in, do it now.")
        print("=" * 60)
        print()
        input("Press Enter when you're logged in and ready...")
        
        # Process songs
        print()
        print("Starting to add songs...")
        print("-" * 60)
        
        successful = 0
        failed = 0
        failed_songs = []
        
        for i, song in enumerate(songs_to_process, start_idx + 1):
            result = add_song_to_library(
                driver,
                song['apple_url'],
                song['spotify_name'],
                song['spotify_artist'],
                i,
                len(found_songs)
            )
            
            if result:
                successful += 1
            else:
                failed += 1
                failed_songs.append(f"{song['spotify_name']} - {song['spotify_artist']}")
            
            # Delay between songs
            time.sleep(DELAY_BETWEEN_SONGS)
        
        print()
        print("=" * 60)
        print("  Complete!")
        print("=" * 60)
        print(f"  ✓ Successfully added: {successful}")
        print(f"  ✗ Failed/Issues: {failed}")
        print()
        
        if failed_songs:
            # Save failed songs to file
            failed_file = os.path.join(export_dir, f"failed_songs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write("Songs that failed to add:\n")
                f.write("=" * 40 + "\n")
                for song in failed_songs:
                    f.write(f"{song}\n")
            print(f"Failed songs saved to: {failed_file}")
        
        print()
        input("Press Enter to close the browser...")
        
    finally:
        driver.quit()
    
    print()
    print("Done! Check your Apple Music library.")


if __name__ == "__main__":
    main()
