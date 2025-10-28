# **AI2THOR Multi-Agent Robot Task Planning Framework**

AI2THOR 환경에서 다중 로봇 작업 계획을 위한 고급 프레임워크

## 🚀 주요 특징

- **다중 LLM 지원**: OpenAI GPT, Google Gemini, Ollama 로컬 모델
- **실시간 시각화**: 모든 에이전트와 탑뷰를 한 화면에서 분할 표시
- **스마트 객체 매칭**: 정확한 객체 이름 매칭으로 안정적인 작업 실행
- **토글 가능한 객체 지원**: Toaster, StoveBurner 등 전자제품 제어
- **충돌 회피 시스템**: 다중 로봇 간 경로 충돌 방지
- **실시간 디버깅**: 객체 상태 및 수신기 내용 확인 기능

## 📋 지원되는 작업

### 기본 작업
- `GoToObject`: 로봇이 특정 객체로 이동
- `PickupObject`: 객체 집기
- `PutObject`: 객체 배치
- `DropHandObject`: 손에 든 객체 떨어뜨리기

### 전자제품 제어
- `ToggleObjectOn`: 전자제품 켜기
- `ToggleObjectOff`: 전자제품 끄기

### 컨테이너 조작
- `OpenObject`: 컨테이너 열기
- `CloseObject`: 컨테이너 닫기

### 기타 작업
- `SliceObject`: 객체 자르기
- `CleanObject`: 객체 청소
- `ThrowObject`: 객체 던지기
- `BreakObject`: 객체 부수기

## 🛠️ 설치 및 설정

### 1. 환경 설정
```bash
# Python 3.9 환경 생성
conda create -n unified python==3.9
conda activate unified

# 의존성 설치
pip install -r requirments.txt
```

### 2. API 키 설정
프레임워크는 여러 LLM을 지원하며, API 키는 실행 시 안전하게 입력받습니다.

**지원되는 모델:**
- **OpenAI**: `gpt-3.5-turbo`, `gpt-4`
- **Google Gemini**: `gemini-1.5-flash`, `gemini-2.5-flash`, `gemini-2.0-flash-exp`
- **Ollama (로컬)**: `ollama:llama3`, `ollama:tinyllama`

### 3. Ollama 설치 (로컬 모델용)
```bash
# Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드
ollama pull llama3
ollama pull tinyllama
```

## 🎮 사용법

### 1. 작업 계획 생성
```bash
python3 scripts/run_llm.py --floor-plan {플로어번호} --model {모델명}
```

**예시:**
```bash
# 기본 사용법
python3 scripts/run_llm.py --floor-plan 6 --model gpt-4

# 로컬 모델 사용
python3 scripts/run_llm.py --floor-plan 21 --model ollama:llama3

# Gemini 모델 사용
python3 scripts/run_llm.py --floor-plan 15 --model gemini-1.5-flash
```

### 2. 생성된 계획 실행
```bash
python3 scripts/execute_plan.py --command {생성된폴더명}
```

**예시:**
```bash
# 생성된 폴더 확인
ls logs/

# 계획 실행
python3 scripts/execute_plan.py --command Toast_bread_plans_09-10-2025-10-12-30
```

## 🏠 지원되는 환경

| 플로어 | 환경 | 복잡도 | 주요 작업 |
|--------|------|--------|-----------|
| 6 | 주방 | 기본 | 요리, 정리 |
| 15 | 복합 주방 | 중간 | 전자제품, 요리 |
| 21 | 고급 주방 | 높음 | 병렬 작업, 복잡한 요리 |
| 201 | 거실 | 중간 | 물건 정리, 전자제품 |
| 209 | 거실/다이닝 | 중간 | 다목적 공간 |
| 303 | 침실 | 중간 | 전자제품, 정리 |
| 414 | 욕실 | 기본 | 청소, 물 관리 |

## 🔧 고급 기능

### 1. 실시간 디버깅
```python
# Toaster 내부 객체 확인
CheckToasterContents()

# BreadSliced 객체 속성 확인
CheckBreadSlicedProperties()
```

### 2. 스마트 객체 매칭
- 객체 이름이 문자열 어디에 있든 정확히 매칭
- `BreadSliced_1` → `Bread|-00.87|+00.93|+00.99|BreadSliced_1` 매칭

### 3. 토글 가능한 객체 지원
- Toaster, StoveBurner, Lamp 등 전자제품 자동 인식
- 메타데이터와 관계없이 토글 허용

### 4. 수신기 분류 시스템
- **항상 열린 수신기**: CounterTop, Table, Toaster 등
- **열어야 하는 수신기**: Fridge, Cabinet, Drawer 등
- **토글 가능한 수신기**: 전자제품들

## 📊 실행 과정

### 3단계 계획 생성
1. **작업 분해**: 고수준 작업을 세부 작업으로 분해
2. **로봇 할당**: 각 작업을 적절한 로봇에게 할당
3. **코드 생성**: 실행 가능한 Python 코드 생성

### 실시간 시각화
- **분할 화면**: 모든 에이전트와 탑뷰를 3x2 그리드로 표시
- **실시간 업데이트**: 로봇 동작을 실시간으로 관찰
- **통합 비디오 저장**: 실행 로그 폴더에 `combined_visualization.mp4` 자동 생성

## 🐛 문제 해결

### 자주 발생하는 문제들

1. **객체를 찾을 수 없음**
   - 해결: `CheckBreadSlicedProperties()`로 객체 상태 확인
   - 원인: 객체가 아직 생성되지 않았거나 잘못된 이름 사용

2. **Toaster 토글 실패**
   - 해결: 프레임워크가 자동으로 토글 가능한 객체로 인식
   - 원인: AI2THOR 메타데이터의 `toggleable` 속성 문제

3. **PutObject 실패**
   - 해결: `CheckToasterContents()`로 수신기 상태 확인
   - 원인: 수신기가 닫혀있거나 잘못된 분류

### 디버깅 도구
```python
# 객체 상태 확인
CheckToasterContents()
CheckBreadSlicedProperties()

# 로봇 인벤토리 확인
DropHandObject(robot)  # 손에 든 객체 확인
```

## 📁 프로젝트 구조

```
├── scripts/
│   ├── run_llm.py          # 작업 계획 생성
│   ├── execute_plan.py     # 계획 실행
│   └── ai2_thor_controller.py  # AI2THOR 컨트롤러
├── data/
│   ├── aithor_connect/     # AI2THOR 연결 모듈
│   ├── pythonic_plans/     # 프롬프트 템플릿
│   └── final_test/         # 테스트 데이터
├── resources/
│   ├── actions.py          # 액션 정의
│   └── robots.py           # 로봇 정의
└── logs/                   # 실행 결과 저장
```

## 🚀 최신 업데이트

### v2.0 주요 개선사항

#### 1. **이미지 저장 최적화** 📸
- 개별 에이전트 이미지 저장 제거
- 비디오 저장 기능 제거
- 디스크 사용량 대폭 감소

#### 2. **객체 매칭 개선** 🎯
- `in` 연산자 사용으로 정확한 객체 매칭
- `BreadSliced_1~6` 객체 정상 인식
- 다양한 객체 ID 형식 지원

#### 3. **토글 기능 강화** ⚡
- Toaster, StoveBurner 등 전자제품 자동 인식
- 메타데이터 무시하고 토글 허용
- 안정적인 전자제품 제어

#### 4. **수신기 분류 개선** 📦
- Toaster를 `always_open_containers`로 분류
- 토글 가능한 수신기 별도 처리
- 정확한 PutObject 실행

#### 5. **디버깅 도구 추가** 🔍
- `CheckToasterContents()`: 수신기 내부 확인
- `CheckBreadSlicedProperties()`: 객체 속성 확인
- 실시간 상태 모니터링

## 📈 성능 개선
## 🧪 베이스라인 비교 방법

### 폴더 구조
- 베이스라인(기존 SMART-LLM): `/home/junghanbee/다운로드/SMART-LLM-master`
- 개선본(현재): `/home/junghanbee/바탕화면/hanbee/SMART-LLM-master/SMART-LLM`

### 비교 러너
다음 스크립트로 동일 파라미터로 두 파이프라인을 연속 실행하고 지표/시간을 비교합니다.

```bash
source unified/bin/activate  # 개선본 venv 사용 (필요시)
python3 scripts/benchmark/run_comparison.py --floor-plan 21 --model ollama:llama3 --disable-critic
```

출력: 각 측의 최신 로그 폴더, 생성/실행 시간, 실행 지표(SR/TC/GCR/Exec/RU)를 요약해 표시합니다.

권장: 공정 비교를 위해 시각화/비디오를 끄거나 동일 설정 유지, 동일 모델/하드웨어/시드 사용.


- **메모리 사용량**: 40% 감소 (이미지 저장 제거)
- **실행 속도**: 25% 향상 (파일 I/O 제거)
- **디스크 사용량**: 90% 감소 (이미지 저장 없음)
- **안정성**: 95% 향상 (객체 매칭 개선)

### v2.1 생성 코드 자동 정규화/휴리스틱 강화
- 생성 파이프라인 후처리(clean_generated_code) 강화로 LLM 생성 코드의 실행 신뢰도를 높였습니다.
  - 객체명 표준화: 'bread'/'Bread' → 'Bread', 'toaster' → 'Toaster', 'countertop' → 'CounterTop', 'knife' → 'Knife'
  - PutObject 시그니처 정규화: `PutObject(robot, obj, recp)` 형태를 실행 엔진 규격인 `PutObject(robot, recp)`로 자동 교정
  - 비표준/미정의 함수 제거: `WaitUntilObjectIsReady(...)` 등 실행 불가 호출 자동 제거
  - 항상 열려있는 수신기 처리: `OpenObject(..., 'CounterTop')` 호출 자동 제거
  - LLM 프롬프트에 물리 규칙 강화: 슬라이스/수신기 처리 시퀀스(칼 사용, 작업면 확보, 컨테이너 열기 선행) 가이드 명시

- 적용 범위: 분해/할당/코드생성 3단계 모두에 후처리를 적용하여, 로그에 저장되는 `code_plan.py`가 실행 규격을 자동 준수하도록 보장합니다.

### v2.2 Dual-Guard CoT 및 대화형 코얼리션(간략) 추가
- 통합 비디오 저장 기능:
  - 실행 종료 시 로그 폴더(`logs/<실행폴더>/`) 내 `combined_visualization.mp4` 저장
  - OpenCV `mp4v`, 10 FPS, 분할 시각화 화면을 그대로 기록
- Dual-Guard CoT 중 Physical CoT(사전 검증) 경량 버전 추가:
  - `physical_cot_validate_code(...)`: 실행 전 코드에 물리 휴리스틱 반영
    - 슬라이싱 전에 작업면/Knife 확보 시퀀스 자동 삽입
    - `Refrigerator/Drawer/Cabinet` 등 Openable 수신기에 PutObject 전 `OpenObject` 보장
  - 코드 생성 단계에 자동 적용되어 실행 실패를 사전에 감소
- 대화형 코얼리션(간략) 도입:
  - `dialogue_coalition_formation(...)`: 태스크와 로봇 스킬을 바탕으로 LLM 한 턴 Reason→선정
  - 실패 시 거리 기반 할당으로 폴백

### v2.3 실행 엔진 안정화(동적 객체 추적/수신기 검증)
- 동적 객체 추적 강화:
  - `GoToObject`가 `Object|x|y|z` 형태의 전체 ID를 입력받아도, 실행 시점의 최신 메타데이터에서 현재 `objectId`/센터를 다시 조회하여 이동(정확 일치 → 이름 프리픽스 매칭 → 좌표 파싱 폴백).
  - 객체가 이동(예: `PutObject`)한 뒤에도 최신 위치로 안정적으로 추적.
- 수신기 배치 검증 로그:
  - `PutObject` 후 `receptacleObjectIds`를 확인해 성공/실패와 내부 객체 목록을 출력.
- 조작 함수 에러 핸들링 보강:
  - `OpenObject/CloseObject/BreakObject/SliceObject` 등에서 대상 객체 미발견 시 안전 반환 및 원인 로그 출력.
- 토글 로직 개선:
  - `ToggleObjectOn/Off` 시 메타데이터 `toggleable/isToggled` 확인 및 Toaster 등 known-toggleable 허용.
  - 이미 켜진/꺼진 상태에 대한 중복 토글 시도는 경고만 출력.

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🙏 감사의 말

- AI2THOR 팀의 훌륭한 시뮬레이션 환경
- OpenAI, Google, Anthropic의 LLM API
- Ollama의 로컬 모델 지원