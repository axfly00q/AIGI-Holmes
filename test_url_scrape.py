"""Quick test to debug URL image scraping."""
import asyncio
import sys
sys.path.insert(0, '.')

from detect import async_fetch_image_urls, async_download_image

async def main():
    # BBC works, so test it
    url = "https://www.bbc.com/news"

    print(f"Testing: {url}")
    try:
        imgs = await async_fetch_image_urls(url)
        print(f"\n✅ Found {len(imgs)} images")
        
        # Try to download first one
        if imgs:
            print(f"\nDownloading first image: {imgs[0][:80]}...")
            img = await async_download_image(imgs[0])
            if img:
                print(f"✅ Downloaded: {img.size}")
            else:
                print("❌ Failed to download")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
)

