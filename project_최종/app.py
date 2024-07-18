from flask import Flask, render_template, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import math
import random
from datetime import datetime
import time
import os
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from konlpy.tag import Okt
from collections import Counter
from matplotlib import font_manager, rc

app = Flask(__name__)

# 한글 폰트 설정
font_path = 'C:/Windows/Fonts/malgun.ttf'  # 윈도우의 경우 맑은고딕 폰트 경로
font_name = font_manager.FontProperties(fname=font_path).get_name()
rc('font', family=font_name)

# 크롬 드라이버 설정
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)  # 크롬 창이 닫히지 않도록 설정
    driver = webdriver.Chrome(options=options)
    return driver

# 데이터 크롤링 함수
def crawl_patents(query, num_patents_required):
    driver = get_driver()
    url = 'http://kpat.kipris.or.kr/kpat/searchLogina.do?next=MainSearch'
    driver.get(url)
    time.sleep(1)

    search = driver.find_element(By.CSS_SELECTOR, "#queryText")
    search.click()
    search.send_keys(query, Keys.ENTER)

    time.sleep(3)  # 페이지가 로드될 시간을 줍니다

    patents_per_page = 30
    num_pages_required = math.ceil(num_patents_required / patents_per_page)
    특허_list = []

    def extract_data():
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        특허s = soup.select('.search_section>article')
        
        for 특허 in 특허s:
            try:
                status_element = 특허.select_one('h1.stitle a')
                status = status_element.text.strip() if status_element else 'N/A'
                
                title_element = 특허.select_one('.search_section_title > h1 > a:nth-child(2)')
                title_full  = title_element.text.strip() if title_element else 'N/A'
                if '(' in title_full and ')' in title_full:
                    title, title_en = title_full.split('(', 1)
                    title_en = title_en.rstrip(')')
                else:
                    title, title_en = title_full, 'N/A'

                IPC_elements = 특허.select('.search_info_list .mainlist_topinfo li:nth-child(1) span.point01')
                IPC_codes = [ipc.text.strip() for ipc in IPC_elements]
                IPC = ', '.join(IPC_codes)
                
                # 출원번호(일자)
                numdate_element = 특허.select_one('.search_info_list .mainlist_topinfo li:nth-child(3) a')
                
                if numdate_element:
                    numdate_text = numdate_element.text.strip()
                    num, date = numdate_text.split(' (')
                    date = date.rstrip(')')
                else:
                    num, date = 'N/A', 'N/A'

                # 출원인 
                applicant_element = 특허.select_one('#mainsearch_info_list > div.mainlist_topinfo > li:nth-child(4) > a > font')
                applicant = applicant_element.text.strip() if applicant_element else 'N/A'
                
                # 최종권리자 
                holder_element = 특허.select_one('#mainsearch_info_list > div.mainlist_topinfo > li.left_width.letter1 > span.point01 > a > font')
                holder = holder_element.text.strip() if holder_element else 'N/A'
                
                # citations 인용횟수
                try:
                    citations_element = 특허.select_one('#mainsearch_info_list > div.mainlist_topinfo > li:nth-child(6) > span.point01 > a')
                    citations = citations_element.text.strip() if citations_element else 'N/A'
                except Exception as e:
                    citations = 'N/A'

                abstract_element = 특허.select_one('.search_txt')
                abstract = abstract_element.text.strip() if abstract_element else 'N/A'

                특허_list.append([status, title, title_en, IPC, num, date, applicant, holder, citations, abstract])
            except Exception as e:
                print(f"Error extracting data: {e}")

    for page in range(num_pages_required):
        extract_data()
        if page < num_pages_required - 1:
            try:
                current_page = (page % 10) + 1
                if current_page == 10:
                    next_button = driver.find_element(By.CSS_SELECTOR, '.board_pager03 a.next')
                    next_button.click()
                else:
                    next_page_number = current_page + 1
                    next_page_button = driver.find_element(By.XPATH, f"//a[text()='{next_page_number}']")
                    next_page_button.click()
                time.sleep(random.uniform(5, 11))
            except Exception as e:
                print(f"Error navigating to the next page: {e}")
                break

    특허_list = 특허_list[:num_patents_required]

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{query}_특허_{num_patents_required}개_{current_time}.xlsx"
    file_path = os.path.join(os.getcwd(), file_name) # 절대 경로로 파일 경로 설정
    df = pd.DataFrame(특허_list, columns=['Status', 'Title', 'Title_EN', 'IPC', 'Application Number', 'Application Date', 'Applicant', 'Holder', 'Citations', 'Abstract'])
    df.to_excel(file_name, index=False, engine='openpyxl')

    driver.quit()
    return file_name

# 형태소 분석기 초기화
okt = Okt()
# 불용어 목록
stopwords = set(['이', '그', '저', '것', '수', '있다', '등', '의', '가', '을', '를', '은', '는', '에', '과', '하고', '이다','머신','러닝','방법','기반','장치','이용','시스템','모델','활용'])

# 텍스트 데이터 전처리 및 명사 추출 함수
def preprocess_text(text):
    tokens = okt.nouns(text)
    tokens = [token for token in tokens if len(token) > 1 and token not in stopwords]
    return tokens

# 제목을 여러 줄로 나누기 함수
def wrap_title(title, max_length=20):
    words = title.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_length:
            current_line += (word + " ")
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        lines.append(current_line.strip())
    return "\n".join(lines)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_patents', methods=['POST'])
def search_patents():
    query = request.json['query']
    num_patents_required = int(request.json['number'])

    if not query or num_patents_required <= 0:
        return jsonify({'error': '검색어와 특허 개수를 올바르게 입력해 주세요.'})

    try:
        excel_file = crawl_patents(query, num_patents_required)
        return jsonify({'excel_file_path': excel_file})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': '특허 데이터를 가져오는 데 실패했습니다.'})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '파일을 업로드해 주세요.'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '파일을 선택해 주세요.'})

    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': '올바른 EXCEL 파일을 업로드해 주세요.'})

    try:
        # EXCEL 파일을 DataFrame으로 읽기
        df = pd.read_excel(file, engine='openpyxl')

        # 날짜 컬럼이 있는 경우, 연도만 추출하여 새로운 컬럼 생성
        df['Application Date'] = pd.to_datetime(df['Application Date'], format='%Y.%m.%d', errors='coerce')
        df['Year'] = df['Application Date'].dt.year

        # 워드클라우드 및 차트 데이터 생성
        words = []
        for text in df['Title'].dropna():
            words.extend(preprocess_text(text))
        word_count = Counter(words)

        # 워드클라우드 생성
        wc = WordCloud(font_path=font_path, background_color='white', width=800, height=600)
        wc.generate_from_frequencies(word_count)

        # 워드클라우드 이미지를 Base64로 인코딩
        buf = io.BytesIO()
        wc.to_image().save(buf, format='PNG')
        wordcloud_image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        # 차트 데이터 준비
        most_common_words = word_count.most_common(10)
        labels, values = zip(*most_common_words)

        chart_data = {
            'labels': labels,  # 상위 10개 단어
            'values': values
        }

        # 피인용 횟수 상위 10개 특허 데이터
        top_cited = df.sort_values(by='Citations', ascending=False).head(10)
        top_cited_titles = top_cited['Title'].apply(lambda x: wrap_title(x, max_length=20)).tolist()
        top_cited_citations = top_cited['Citations'].tolist()

        top_cited_data = {
            'labels': top_cited_titles,
            'values': top_cited_citations
        }

        return jsonify({
            'chart_data': chart_data,
            'wordcloud': wordcloud_image_base64,
            'top_cited': top_cited_data
        })
    except Exception as e:
        print(f"Error uploading and analyzing file: {e}")
        return jsonify({'error': '파일 분석에 실패했습니다.'})

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(os.getcwd(), filename)  # 절대 경로로 파일 경로 설정
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
