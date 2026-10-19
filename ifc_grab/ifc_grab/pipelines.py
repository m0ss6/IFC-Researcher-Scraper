# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import json
from pathlib import Path


class FinalOutputPipeline:
    def close_spider(self, spider):
        # Access the spider's whole_scrape variable directly
        if hasattr(spider, 'whole_scrape'):
            output_dir = Path(spider.settings.get('OUTPUT_DIR', 'data'))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / 'output.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(spider.whole_scrape, f, ensure_ascii=False, indent=2)
            spider.logger.info(f"Saved data from whole_scrape to {output_path}")
        else:
            spider.logger.error("whole_scrape variable not found in spider")
