# 이미지 썸네일 변환 도구

제품 이미지를 1024x1024 크기의 썸네일로 자동 변환하는 Python 스크립트입니다.

## 주요 기능

- ✨ 다양한 이미지 형식 지원 (JPG, PNG, BMP, GIF, WebP, TIFF)
- 📐 원본 비율 유지하면서 1024x1024(또는 지정 크기)로 변환
- 🎨 흰색 배경에 이미지 중앙 배치
- 🧱 이미지와 캔버스 가장자리 사이 최소 130px 여백(기본값, 변경 가능)
- 🚀 디렉토리 내 모든 이미지 일괄 처리
- ⚙️ 커스터마이징 가능한 크기, 품질, 패딩 설정

## 설치 방법

1. Python 설치 확인 (Python 3.7 이상 필요)
```bash
python --version
```

2. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

또는 직접 설치:
```bash
pip install Pillow
```

## 사용 방법

### 기본 사용법

현재 디렉토리의 모든 이미지를 변환:
```bash
python image_thumbnail_converter.py
```

변환된 이미지는 `./thumbnails` 폴더에 저장됩니다.

### 고급 사용법

**특정 디렉토리의 이미지 변환:**
```bash
python image_thumbnail_converter.py -i ./제품이미지
```

**출력 디렉토리 지정:**
```bash
python image_thumbnail_converter.py -i ./제품이미지 -o ./썸네일
```

**크기 변경 (예: 512x512):**
```bash
python image_thumbnail_converter.py -s 512 512
```

**품질 조정 (예: 85%):**
```bash
python image_thumbnail_converter.py -q 85
```

**패딩(여백) 변경 (예: 최소 100px):**
```bash
python image_thumbnail_converter.py -p 100
```

**모든 옵션 조합:**
```bash
python image_thumbnail_converter.py -i ./images -o ./output -s 800 800 -q 90 -p 130
```

## 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `-i, --input` | 입력 이미지 디렉토리 | 현재 디렉토리 |
| `-o, --output` | 출력 디렉토리 | 입력디렉토리/thumbnails |
| `-s, --size` | 썸네일 크기 (너비 높이) | 1024 1024 |
| `-q, --quality` | JPEG 품질 (1-100) | 95 |
| `-p, --padding` | 이미지와 캔버스 가장자리 사이 최소 여백(px) | 130 |

## 도움말 보기

```bash
python image_thumbnail_converter.py -h
```

## 예시 시나리오

### 시나리오 1: 쇼핑몰 제품 이미지 변환
```bash
# 제품 이미지 폴더의 모든 이미지를 썸네일로 변환
python image_thumbnail_converter.py -i "C:\제품사진" -o "C:\썸네일"
```

### 시나리오 2: 고품질 썸네일 생성
```bash
# 최고 품질로 썸네일 생성
python image_thumbnail_converter.py -i ./images -q 100
```

### 시나리오 3: 작은 썸네일 생성
```bash
# 512x512 크기의 작은 썸네일 생성
python image_thumbnail_converter.py -i ./images -s 512 512
```

## 처리 과정

1. 입력 디렉토리에서 지원되는 이미지 파일 검색
2. 각 이미지를 로드하여 RGB로 변환
3. (필요 시) 흰색 배경 여백 제거로 실제 콘텐츠 영역만 추출
4. 원본 비율을 유지하면서, 캔버스 크기에서 패딩(좌우/상하 2배)을 뺀 최대 영역 안에 맞게 리사이즈
5. 지정 크기의 흰색 캔버스(기본 1024x1024)에 중앙 배치
6. JPEG 형식으로 최적화하여 저장

## 지원 이미지 형식

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- GIF (.gif)
- WebP (.webp)
- TIFF (.tiff, .tif)

## 출력 형식

- 모든 이미지는 JPEG 형식으로 저장됩니다
- 파일명: `원본파일명_thumbnail.jpg`
- 투명 배경은 흰색으로 변환됩니다

## 주의사항

- 원본 이미지는 변경되지 않습니다
- 출력 디렉토리가 없으면 자동으로 생성됩니다
- 동일한 이름의 파일이 있으면 덮어씁니다

## 문제 해결

**Pillow 설치 오류:**
```bash
pip install --upgrade pip
pip install Pillow
```

**권한 오류:**
관리자 권한으로 실행하거나 다른 출력 디렉토리를 지정하세요.

## 라이센스

이 도구는 자유롭게 사용 및 수정 가능합니다.
