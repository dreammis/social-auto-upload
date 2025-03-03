from bs4 import BeautifulSoup
import sys

def clean_html(input_file, output_file):
    # 读取原始文件
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(content, 'html.parser')

    # 移除所有style标签
    for style in soup.find_all('style'):
        style.decompose()

    # 移除所有class和style属性
    for tag in soup.find_all(True):
        if tag.has_attr('class'):
            del tag['class']
        if tag.has_attr('style'):
            del tag['style']

    # 保存清理后的文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))

if __name__ == '__main__':
    input_file = 'error_logs/cookie_gen_20250220_200544.html'
    output_file = 'error_logs/cookie_gen_20250220_200544_clean.html'
    clean_html(input_file, output_file)
    print("HTML文件已清理完成！") 