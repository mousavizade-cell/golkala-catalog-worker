# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import sys
from urllib.parse import urljoin

# تابع تبدیل اعداد فارسی به انگلیسی
def persian_to_english_digits(s: str) -> str:
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    for p, e in zip(persian_digits, english_digits):
        s = s.replace(p, e)
    return s

# تابع استخراج مشخصات یک محصول از بلوک HTML
def parse_product_card(card, base_url):
    # نام محصول
    name_tag = card.select_one('.product-title a')
    name = name_tag.get_text(strip=True) if name_tag else ''

    # لینک محصول
    rel_link = name_tag['href'] if name_tag and 'href' in name_tag.attrs else ''
    link = urljoin(base_url, rel_link)

    # قیمت
    price_tag = card.select_one('.price')
    price_text = price_tag.get_text() if price_tag else ''
    price_text = persian_to_english_digits(price_text)
    # استخراج عدد
    price_match = re.search(r'(\d+)', price_text.replace(',', ''))
    price = int(price_match.group(1)) if price_match else 0

    # توضیح کوتاه و ویژگی‌ها
    desc_tag = card.select_one('.short-description')
    desc = desc_tag.get_text(' ، ', strip=True) if desc_tag else ''
    # برچسب ⚙️ در صورت یافتن کلمات آموزشی یا آسانکار
    if re.search(r'آموزشی|آسانکار', desc):
        desc = '⚙️ ' + desc

    # دسته و زیردسته (بقایای مسیر breadcrumb در همان کارت یا صفحه)
    breadcrumb = card.select_one('.breadcrumb')
    if breadcrumb:
        crumbs = [c.get_text(strip=True) for c in breadcrumb.select('li') if c.get_text(strip=True)]
        category = '/'.join(crumbs)
    else:
        category = ''

    # وضعیت موجودی (اختیاری)
    stock_tag = card.select_one('.stock-status')
    stock = stock_tag.get_text(strip=True) if stock_tag else ''

    return {
        'نام محصول': name,
        'قیمت (تومان)': price,
        'توضیحات': desc,
        'دسته/زیردسته': category,
        'لینک': link,
        'موجودی': stock
    }

# تابع پیمایش صفحات یک دسته
def scrape_category(category_url):
    products = []
    page = 1
    while True:
        url = f"{category_url}?page={page}"
        print(f"در حال پردازش صفحه {page} : {url}")
        resp = requests.get(url)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, 'html.parser')

        # پیدا کردن کارت‌های محصولات
        cards = soup.select('.product-item')
        if not cards:
            break

        for card in cards:
            prod = parse_product_card(card, category_url)
            products.append(prod)

        # بررسی وجود لینک صفحه بعد
        next_btn = soup.select_one('.pagination .next')
        if not next_btn or 'disabled' in next_btn.get('class', []):
            break
        page += 1

    return products

def main():
    if len(sys.argv) < 2:
        print("Usage: python golkala_scraper.py <category_url>")
        sys.exit(1)

    category_url = sys.argv[1].rstrip('/')
    # استخراج نام دسته برای نام فایل
    category_name = category_url.split('/')[-1]
    output_filename = f"Golkala_Catalog_{category_name}.xlsx"

    # 1. پیمایش و استخراج محصولات
    data = scrape_category(category_url)

    if not data:
        print("محصولی یافت نشد.")
        sys.exit(0)

    # 2. ساخت DataFrame و افزودن ستون ردیف
    df = pd.DataFrame(data)
    df.insert(0, 'ردیف', range(1, len(df) + 1))

    # 3. ذخیره در Excel
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        df.to_excel(writer,
                    sheet_name='کاتالوگ نمایندگان',
                    index=False)

        # 4. خلاصه آماری
        total_products = len(df)
        price_min = df['قیمت (تومان)'].min()
        price_max = df['قیمت (تومان)'].max()
        price_avg = int(df['قیمت (تومان)'].mean())
        template_count = df['توضیحات'].str.contains('⚙️').sum()

        summary_df = pd.DataFrame({
            'آمار': ['تعداد کل محصولات', 'کمترین قیمت (تومان)', 'بیشترین قیمت (تومان)',
                    'میانگین قیمت (تومان)', 'تعداد محصولات با فایل جانبی'],
            'مقدار': [total_products, price_min, price_max, price_avg, template_count]
        })
        summary_df.to_excel(writer,
                            sheet_name='خلاصه آماری',
                            index=False)

    print(f"❇️ فایل Excel با نام '{output_filename}' با موفقیت ساخته شد.")
    print("خلاصه آماری:")
    print(summary_df.to_string(index=False))

if __name__ == "__main__":
    main()

3. طرز کار  
   - اجرای اسکریپت به صورت:
```bash
python golkala_scraper.py https://golkala.ir/category/لوازم-آرایشی
     ```  
   - اسکریپت صفحات را پشت‌سرهم پیمایش می‌کند، اطلاعات هر محصول را استخراج کرده و در DataFrame می‌ریزد.  
   - در انتها دو شیت در فایل Excel تولید می‌شود:  
     1. “کاتالوگ نمایندگان” با ستون‌های ردیف، نام محصول، قیمت، توضیحات (با برچسب ⚙️ اگر فایل جانبی باشد)، دسته/زیردسته، لینک و موجودی  
     2. “خلاصه آماری” شامل:
     - تعداد کل محصولات  
     - کمترین قیمت  
     - بیشترین قیمت  
     - میانگین قیمت  
     - تعداد محصولات دارای فایل جانبی

4. نتیجه نهایی  
   فایل Excel رسمی و فارسی `Golkala_Catalog_[نام_دسته].xlsx` که آماده‌ی چاپ یا ارسال به نمایندگان فروش است.  
   لطفاً در صورت نیاز به شخصی‌سازی بیشتر (مثلاً تغییر سلکتورهای CSS یا فرمت‌بندی) بفرمایید تا در اسرع وقت اصلاح گردد.
