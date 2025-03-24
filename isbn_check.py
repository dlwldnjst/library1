import streamlit as st
import pandas as pd
import io
from io import StringIO
import re
import subprocess
import sys

st.title("ISBN 중복 도서 지우개 ")
# 버튼 스타일의 링크 추가
st.markdown(
    """
    <a href="https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdn%2FBAz3g%2FbtsJwqOEUO0%2FtoZvMwgk0F4XpPzg21lEjK%2Fimg.png" target="_blank" style="text-decoration: none;">
        <br>
        <div style="
            display: inline-block;
            padding: 8px 12px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            background-color: #00418a;
            border-radius: 5px;
            text-align: center;">
            📘 독서로에서 ISBN이 포함된 소장도서목록 다운받는 방법
        </div>
        <br>
        <br>
    </a>
    <br>
    """,
    unsafe_allow_html=True
)

# 필요한 패키지 설치 확인 및 설치
required_packages = ['html5lib', 'lxml', 'bs4']
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        st.warning(f"{package} 패키지를 설치합니다...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        st.success(f"{package} 패키지가 설치되었습니다.")

# 헤더(컬럼명)가 첫 행에 있다고 가정 (필요에 따라 수정)
skiprows_lib = 0
skiprows_pur = 0

# 파일 업로드
lib_file = st.file_uploader("소장 도서 목록 파일 업로드 (.xls 또는 .xlsx)", type=["xls", "xlsx"])
pur_file = st.file_uploader("구매 예정 파일 업로드 (.xls 또는 .xlsx)", type=["xls", "xlsx"])

<br> 구매 예정 파일을 업로드할 때 오류가 날 경우, xls 파일을 xlsx로 저장 후 다시 시도해주세요 :)

def extract_first_table(html_text):
    """정규표현식을 사용해 첫 번째 <table>...</table> 블록 추출"""
    pattern = re.compile(r'(<table.*?</table>)', re.DOTALL | re.IGNORECASE)
    match = pattern.search(html_text)
    if match:
        return match.group(1)
    return None

def read_uploaded_file(file, skiprows=0):
    """
    업로드된 파일을 먼저 pd.read_excel로 읽어보고, 실패 시(예: HTML 형식인 경우)
    파일 내용을 텍스트로 디코딩하여 pd.read_html (또는 추출된 <table> 블록) 방식으로 DataFrame으로 변환.
    파일 확장자가 xls 또는 xlsx인 경우 우선 엑셀 파일로 읽습니다.
    """
    try:
        content = file.getvalue()
    except Exception as e:
        st.error(f"파일 내용을 읽어오는 데 실패했습니다: {e}")
        st.stop()
    
    file_extension = file.name.split('.')[-1].lower()
    
    # 우선 Excel 파일로 읽어보기
    if file_extension in ['xls', 'xlsx']:
        try:
            if file_extension == 'xls':
                df = pd.read_excel(io.BytesIO(content), engine='xlrd', skiprows=skiprows)
            else:
                df = pd.read_excel(io.BytesIO(content), engine='openpyxl', skiprows=skiprows)
            return df
        except Exception as excel_error:
            st.warning(f"Excel 파일로 읽기 실패: {excel_error}")
            st.info("Excel 파일 읽기에 실패하여 HTML 변환을 시도합니다.")
    
    # Excel 읽기가 실패했거나 파일 형식이 다른 경우, 텍스트로 디코딩하여 HTML 방식으로 시도
    try:
        content_text = content.decode('utf-8-sig', errors='ignore')
    except Exception as e:
        st.error(f"파일 내용을 텍스트로 디코딩하는 데 실패했습니다: {e}")
        st.stop()
    
    # HTML 태그 여부 확인 (대소문자 무시)
    if re.search(r'<html|<table|<tr|<td', content_text, re.IGNORECASE):
        st.info("HTML 형식의 파일로 감지되어 처리합니다.")
        html_parsers = ['html5lib', 'lxml', 'bs4']
        df_list = None
        for parser in html_parsers:
            try:
                df_list = pd.read_html(StringIO(content_text), flavor=parser)
                if df_list and len(df_list) > 0:
                    st.info(f"{parser} 파서로 테이블을 찾았습니다.")
                    break
            except Exception as e:
                st.warning(f"{parser} 파서로 HTML 읽기 실패: {e}")
                continue
        
        # pd.read_html로 테이블을 찾지 못한 경우, 첫 번째 <table> 블록 추출 후 다시 시도
        if not df_list or len(df_list) == 0:
            st.info("pd.read_html로 테이블을 찾지 못했습니다. 첫 번째 <table> 블록을 추출하여 다시 시도합니다.")
            table_html = extract_first_table(content_text)
            if table_html:
                try:
                    df_list = pd.read_html(StringIO(table_html), flavor='html5lib')
                except Exception as e:
                    st.error(f"추출된 HTML 블록으로 테이블 읽기 실패: {e}")
            else:
                st.error("HTML에서 <table> 태그를 찾을 수 없습니다.")
        
        if df_list and len(df_list) > 0:
            # 가장 큰 테이블 선택 (행*열 수가 최대인 테이블)
            largest_df = max(df_list, key=lambda df: df.shape[0] * df.shape[1])
            return largest_df
        else:
            raise ValueError("HTML 테이블을 읽을 수 없습니다.")
    else:
        # HTML 태그가 없는 경우, CSV 형식으로 시도
        try:
            return pd.read_csv(StringIO(content_text))
        except Exception as csv_error:
            st.warning(f"CSV 형식으로 읽기 실패: {csv_error}")
        
        raise ValueError("파일 형식을 인식할 수 없습니다. 지원되는 형식인지 확인하세요.")

if lib_file is not None and pur_file is not None:
    # 소장 도서 목록 읽기
    try:
        lib_df = read_uploaded_file(lib_file, skiprows=skiprows_lib)
    except Exception as e:
        st.error(f"소장 도서 목록 파일을 읽는 데 실패했습니다: {e}")
        st.stop()
    
    # 구매 예정 파일 읽기
    try:
        pur_df = read_uploaded_file(pur_file, skiprows=skiprows_pur)
    except Exception as e:
        st.error(f"구매 예정 파일을 읽어오는 데 실패했습니다: {e}")
        st.stop()
    
    # 데이터 미리보기 (컬럼명은 그대로, 데이터 미리보기만 표시)
    st.subheader("소장 도서 목록 미리보기")
    st.dataframe(lib_df.head())

    st.subheader("구매 예정 목록 미리보기")
    st.dataframe(pur_df.head())
    
    # ISBN 컬럼 선택: 'ISBN13'이 있으면 우선 선택
    st.subheader("소장 도서 목록의 ISBN(또는 ISBN13) 컬럼 선택")
    def get_default_isbn_col(df):
        cols = df.columns.tolist()
        if "ISBN13" in cols:
            return "ISBN13"
        elif "ISBN" in cols:
            return "ISBN"
        else:
            return cols[0]
    
    default_lib_isbn = get_default_isbn_col(lib_df)
    lib_isbn_col = st.selectbox("소장 도서 목록에서 ISBN 컬럼 선택", 
                                options=lib_df.columns.tolist(),
                                index=lib_df.columns.tolist().index(default_lib_isbn))
    
    st.subheader("구매 예정 목록의 ISBN(또는 ISBN13) 컬럼 선택")
    default_pur_isbn = get_default_isbn_col(pur_df)
    pur_isbn_col = st.selectbox("구매 예정 목록에서 ISBN 컬럼 선택", 
                                options=pur_df.columns.tolist(),
                                index=pur_df.columns.tolist().index(default_pur_isbn))
    
    # ISBN 정제 함수: 좌우 공백 제거, 하이픈 제거, 대문자 변환 등
    def clean_isbn(series):
        cleaned = series.astype(str).str.strip().str.replace("-", "", regex=False).str.upper()
        cleaned = cleaned.replace("NAN", "").replace("", pd.NA)
        return cleaned

    if st.button("ISBN 중복 검사"):
        # ISBN 정제 적용
        lib_df[lib_isbn_col] = clean_isbn(lib_df[lib_isbn_col])
        pur_df[pur_isbn_col] = clean_isbn(pur_df[pur_isbn_col])

        # 소장 도서 목록은 ISBN이 유효한 (13자리) 행만 남김
        lib_isbn_valid = lib_df[lib_isbn_col].astype(str).str.len() == 13
        lib_df = lib_df[lib_isbn_valid].dropna(subset=[lib_isbn_col])
        
        # 구매 예정 목록은 ISBN 칼럼이 있는 행만 대상으로 중복 제거하되,
        # ISBN이 없는 행은 그대로 유지 (즉, ISBN이 있는 행 중에서만 제거)
        # 따라서 중복 체크 대상은 ISBN 값이 존재하면서 길이가 13인 행입니다.
        mask = pur_df[pur_isbn_col].notna() & (pur_df[pur_isbn_col].astype(str).str.len() == 13) & (pur_df[pur_isbn_col].isin(lib_df[lib_isbn_col]))
        duplicate_isbns = set(pur_df.loc[mask, pur_isbn_col])
        duplicate_count = len(duplicate_isbns)
        
        st.subheader("중복된 ISBN 목록")
        if duplicate_isbns:
            st.warning(f"총 {duplicate_count}개의 ISBN이 중복됩니다:")
            st.write(duplicate_isbns)
        else:
            st.info("중복된 ISBN이 없습니다.")
        
        # 중복 제거 후 구매 예정 목록 생성: ISBN이 존재하며 라이브러리 목록에 있는 행만 제거
        output_df = pur_df.copy()
        output_df = output_df[~mask].copy()
        removed_count = pur_df.shape[0] - output_df.shape[0]
        st.info(f"총 {removed_count} 권의 중복 도서가 제거되었습니다.")
        
        # 번호(순번) 칼럼 재설정: 기존 '순번' 칼럼이 있으면 덮어쓰고, 없으면 새로 삽입하여 1부터 연속된 번호를 부여
        output_df.reset_index(drop=True, inplace=True)
        if "순번" in output_df.columns:
            output_df["순번"] = range(1, len(output_df) + 1)
        else:
            output_df.insert(0, "순번", range(1, len(output_df) + 1))
        
        st.subheader("중복 제거 후 구매 예정 목록 미리보기")
        st.dataframe(output_df)
        
        # 파일 다운로드 처리 (결과는 XLSX 형식, 원본 구매 예정 목록과 동일한 형식)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            output_df.to_excel(writer, index=False)
        buffer.seek(0)
        
        st.download_button(
            label="필터링된 파일 다운로드",
            data=buffer,
            file_name="filtered_purchase_list.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
