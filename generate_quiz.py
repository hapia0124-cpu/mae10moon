import os
import json
import requests
import feedparser
from datetime import datetime, timezone, timedelta
import base64
import time

# === 설정 ===
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_OWNER = 'hapia0124-cpu'
GITHUB_REPO = 'mae10moon'

# KST 오늘 날짜
kst = datetime.now(timezone.utc) + timedelta(hours=9)
today = kst.strftime('%Y-%m-%d')
print(f"오늘 날짜: {today}")

# === 1. RSS 뉴스 수집 ===
RSS_FEEDS = [
    ('한국경제', 'https://www.hankyung.com/feed/economy', 25),
    ('연합경제', 'https://www.yonhapnewstv.co.kr/category/news/economy/feed/', 25),
    ('매일경제', 'https://www.mk.co.kr/rss/30000001/', 25),
]

articles = []
for name, url, limit in RSS_FEEDS:
    try:
        feed = feedparser.parse(url)
        count = 0
        for entry in feed.entries:
            if count >= limit:
                break
            title = entry.get('title', '').replace('<![CDATA[', '').replace(']]>', '').strip()
            link = entry.get('link', '')
            if title:
                articles.append({'title': title, 'link': link})
                count += 1
        print(f"{name}: {count}개 수집")
    except Exception as e:
        print(f"RSS 오류 {name}: {e}")

# 네이버 경제 뉴스
try:
    naver_client_id = os.environ.get('NAVER_CLIENT_ID', '')
    naver_client_secret = os.environ.get('NAVER_CLIENT_SECRET', '')
    if naver_client_id:
        res = requests.get(
            'https://openapi.naver.com/v1/news/today.json',
            headers={
                'X-Naver-Client-Id': naver_client_id,
                'X-Naver-Client-Secret': naver_client_secret
            },
            params={'category': 'economic', 'count': 30}
        )
        if res.status_code == 200:
            items = res.json().get('channel', {}).get('item', [])
            for item in items:
                title = item.get('title', '').replace('<b>', '').replace('</b>', '')
                link = item.get('link', '')
                if title:
                    articles.append({'title': title, 'link': link})
            print(f"네이버: {len(items)}개 수집")
except Exception as e:
    print(f"네이버 오류: {e}")

print(f"총 수집된 기사: {len(articles)}개")
title_list = '\n'.join([f"{i}. {a['title']} | {a['link']}" for i, a in enumerate(articles)])

# === 2. Gemini로 퀴즈 생성 (재시도 포함) ===
prompt = f"""너는 금융권 취업 준비생을 위한 퀴즈 출제자야.
아래 오늘의 경제 뉴스 제목들을 보고 퀴즈 10개를 만들어줘.
퀴즈 구성 우선순위:
1순위 - 뉴스에 금융 신조어나 최신 용어가 있으면 → 정의를 주고 용어를 맞추는 문제 (있는 만큼만). 오답 선지는 해당 용어와 혼동하기 쉬운 유사 개념으로 구성하고, 미세한 차이를 구분해야 맞출 수 있게 난도를 높여.
2순위 - 뉴스에 특정 금융상품/제도가 자주 언급되면 → 세부 지식 문제 최대 3개 (한도, 조건 등)
3순위 - 나머지는 금융권 필기/시사상식 대비 문제로 채우기. 단순 사실 확인이 아니라, 해당 뉴스가 은행 경영·여신·수신·금리정책에 미치는 영향이나 금융당국 대응을 묻는 문제로 출제. 금융권 취준 필기시험에 나올 법한 수준으로. 최대 4개
공통 조건:
- 4지선다 (오답 3개는 비슷한 용어나 개념으로 헷갈리게)
- 해설은 한 문장으로 간단하게, 정답 해설 한 문장 뒤에, 오답 선지만 골라서 왜 틀렸는지 각각 한 문장씩 추가. 정답 선지는 제외
- "옳은 것은?" 또는 "옳지 않은 것은?" 유형은 최대 3개로 제한
- 선지는 최대한 간결하게
- JSON 형식으로만 출력 (마크다운 기호 쓰지 마)
- date는 반드시 "{today}"를 사용할 것. 뉴스 날짜를 참고하지 말 것.
- 아래는 실제 금융권 필기시험 기출 유형 예시입니다. 이 수준과 스타일을 참고해서 출제하세요:
  [금융용어 출제 예시]
  - COFIX: 은행 대출금리의 기준이 되는 자금조달비용지수
  - 스무딩오퍼레이션: 환율이 한 방향으로 급격히 움직일 때 중앙은행이 개입해 완화하는 것
  - 핫머니: 선진국 저금리 정책으로 조달비용이 낮아진 유동성 자금
  - 빅배스: 부실요소를 한 회계연도에 모두 반영하는 것
  - 필립스 곡선: 실업률과 물가상승률의 반비례 관계
  - 투키디데스 함정: 신흥 세력이 지배 세력을 위협할 때 발생하는 구조적 긴장
  [세부지식 출제 예시]
  - KIKO(Knock-In Knock-Out) 통화옵션: 옵션 구조, 조건, 리스크에 대한 세부 지식 문제
  - 레버리지 ETF: 2배 레버리지 구조, 장단점에 대한 세부 지식 문제
JSON 형식:
[
  {{
    "date": "{today}",
    "category": "금융용어 또는 시사 또는 세부지식",
    "question": "문제",
    "options": ["①", "②", "③", "④"],
    "answer": "정답",
    "explanation": "정답 해설 한 문장. [오답해설] ① 설명 ② 설명 ③ 설명 ④ 설명 (정답 선지는 제외)",
    "news_context": "이 문제와 가장 관련된 기사 제목 또는 핵심 내용을 한 문장으로. 숫자 인덱스 절대 포함하지 말 것.",
    "news_url": "위 뉴스 목록에서 이 문제와 관련된 기사의 URL. 없으면 null"
  }}
]
뉴스 제목:
{title_list}"""

quizzes = None
for attempt in range(5):
    try:
        print(f"Gemini 호출 시도 {attempt+1}/5")
        gemini_res = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}',
            json={{'contents': [{{'parts': [{{'text': prompt}}]}}]}},
            timeout=120
        )
        if gemini_res.status_code == 200:
            raw = gemini_res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0]
            quizzes = json.loads(raw)
            print(f"퀴즈 생성 성공: {len(quizzes)}개")
            break
        elif gemini_res.status_code == 503:
            wait = 60 * (attempt + 1)
            print(f"503 과부하, {wait}초 후 재시도...")
            time.sleep(wait)
        else:
            raise Exception(f"Gemini 오류: {gemini_res.status_code} {gemini_res.text}")
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}, 재시도...")
        time.sleep(30)

if not quizzes:
    raise Exception("Gemini 5회 시도 모두 실패")

# === 3. Supabase 저장 ===
headers = {{
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {{SUPABASE_KEY}}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}}

saved_quizzes = []
for q in quizzes:
    res = requests.post(
        f'{{SUPABASE_URL}}/rest/v1/Quiz',
        headers=headers,
        json={{
            'date': q['date'],
            'category': q['category'],
            'question': q['question'],
            'options': q['options'],
            'answer': q['answer'],
            'explanation': q['explanation'],
            'news_context': q.get('news_context', ''),
            'news_url': q.get('news_url', None)
        }}
    )
    if res.status_code in [200, 201]:
        saved_quizzes.append(res.json()[0] if res.json() else q)
    else:
        print(f"Supabase 저장 오류: {{res.status_code}}")
        saved_quizzes.append(q)

print(f"Supabase 저장 완료: {{len(saved_quizzes)}}개")

# === 4. quiz HTML 생성 ===
quizzes_json = json.dumps(saved_quizzes, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e')

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{today}} 금융 퀴즈 10문제 - 매십문</title>
<meta name="description" content="{{today}} 매십문 금융 퀴즈 10문제. 매일 업데이트되는 금융/경제 퀴즈로 금융 자격증을 준비하세요.">
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Noto+Sans+KR:wght@400;700;900&family=Black+Han+Sans&display=swap" rel="stylesheet">
<style>
:root{{--sky:#5bc8f5;--pink:#ff6eb4;--pink-dark:#d94f96;--yellow:#ffd700;--yellow-dark:#e6a800;--cream:#fff8e7;--navy:#1a1a6e;--purple:#8b5cf6;--green:#22c55e;--green-dark:#16a34a;--red:#ef4444;--white:#ffffff;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--sky);font-family:'Press Start 2P',monospace;min-height:100vh;overflow-x:hidden;padding-bottom:2rem;}}
.wrap{{max-width:640px;margin:0 auto;padding:1rem;}}
.bg{{position:fixed;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:0;}}
.cloud{{position:absolute;background:white;}}.cloud::before,.cloud::after{{content:'';position:absolute;background:white;}}
.c1{{width:48px;height:16px;top:12%;left:5%;animation:cloudMove 18s linear infinite;}}.c1::before{{width:24px;height:16px;top:-12px;left:8px;}}.c1::after{{width:16px;height:12px;top:-8px;left:24px;}}
.c2{{width:96px;height:24px;top:8%;left:55%;animation:cloudMove 26s linear infinite 4s;}}.c2::before{{width:48px;height:24px;top:-18px;left:16px;}}.c2::after{{width:32px;height:16px;top:-10px;left:52px;}}
.c3{{width:140px;height:32px;top:18%;left:20%;animation:cloudMove 35s linear infinite 10s;}}.c3::before{{width:72px;height:32px;top:-24px;left:24px;}}.c3::after{{width:48px;height:20px;top:-14px;left:72px;}}
@keyframes cloudMove{{0%{{transform:translateX(-200px)}}100%{{transform:translateX(110vw)}}}}
.content{{position:relative;z-index:1;}}
.title-card{{background:var(--cream);border:6px solid var(--navy);box-shadow:8px 8px 0 var(--navy);padding:1.5rem;margin-bottom:1.5rem;text-align:center;position:relative;}}
.title-card::before{{content:'';position:absolute;top:-6px;left:-6px;right:-6px;bottom:-6px;border:3px solid var(--pink);pointer-events:none;}}
.title-main{{font-family:'Black Han Sans',sans-serif;font-size:clamp(3rem,12vw,5rem);color:#5bc8f5;-webkit-text-stroke:4px var(--navy);text-shadow:6px 6px 0 var(--navy);line-height:1.2;margin-bottom:0.5rem;letter-spacing:4px;}}
.title-sub{{font-size:0.45rem;color:var(--purple);letter-spacing:1px;}}
.date-badge{{display:inline-block;margin-top:0.8rem;background:var(--navy);color:var(--yellow);border:3px solid var(--yellow);padding:4px 12px;font-size:0.5rem;}}
.progress-wrap{{background:var(--navy);border:4px solid #000;height:24px;margin-bottom:1.5rem;position:relative;box-shadow:4px 4px 0 #000;}}
.progress-bar{{height:100%;background:var(--yellow);transition:width 0.3s steps(8);}}
.progress-label{{position:absolute;right:8px;top:50%;transform:translateY(-50%);font-size:0.5rem;color:var(--navy);}}
.quiz-card{{background:var(--cream);border:4px solid var(--navy);box-shadow:8px 8px 0 var(--navy);padding:1.5rem;margin-bottom:1.5rem;animation:popIn 0.2s steps(4) forwards;}}
@keyframes popIn{{0%{{transform:scale(0.95);opacity:0}}100%{{transform:scale(1);opacity:1}}}}
.category-tag{{display:inline-block;padding:0.4rem 0.8rem;font-size:0.6rem;margin-bottom:1rem;border:3px solid;}}
.tag-금융용어{{background:var(--yellow);color:var(--navy);border-color:var(--yellow-dark);}}.tag-시사{{background:var(--green);color:white;border-color:var(--green-dark);}}.tag-세부지식{{background:var(--purple);color:white;border-color:#6d28d9;}}.tag-default{{background:var(--pink);color:white;border-color:var(--pink-dark);}}
.question-text{{font-family:'Noto Sans KR',sans-serif;font-size:0.95rem;line-height:1.8;color:var(--navy);margin-bottom:1.5rem;font-weight:700;}}
.options{{display:flex;flex-direction:column;gap:0.8rem;}}
.option{{background:var(--white);border:4px solid var(--navy);box-shadow:4px 4px 0 var(--navy);padding:0.8rem 1rem;cursor:pointer;font-family:'Noto Sans KR',sans-serif;font-size:0.85rem;font-weight:700;color:var(--navy);text-align:left;width:100%;transition:transform 0.1s steps(2),box-shadow 0.1s steps(2);line-height:1.5;}}
.option:hover:not(:disabled){{transform:translate(-2px,-2px);box-shadow:6px 6px 0 var(--navy);background:var(--yellow);}}
.option.correct{{background:var(--green)!important;color:white!important;border-color:var(--green-dark)!important;animation:correctFlash 0.3s steps(2) 2;}}
.option.wrong{{background:var(--red)!important;color:white!important;border-color:#b91c1c!important;animation:wrongShake 0.3s steps(3);}}
.option:disabled{{cursor:default;}}
@keyframes correctFlash{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}
@keyframes wrongShake{{0%{{transform:translateX(0)}}25%{{transform:translateX(-6px)}}75%{{transform:translateX(6px)}}100%{{transform:translateX(0)}}}}
.explanation{{display:none;background:var(--navy);color:var(--cream);border:4px solid #000;padding:1.2rem;margin-top:1rem;font-family:'Noto Sans KR',sans-serif;font-size:0.82rem;line-height:1.8;}}
.explanation.show{{display:block;}}
.exp-label{{font-family:'Press Start 2P',monospace;font-size:0.5rem;color:var(--yellow);margin-bottom:0.8rem;}}
.news-ctx{{margin-top:0.8rem;padding:0.6rem;background:rgba(255,255,255,0.1);border-left:4px solid var(--yellow);font-size:0.78rem;color:var(--cream);}}
.news-link{{color:var(--yellow);text-decoration:underline;}}
.nav-buttons{{display:flex;gap:0.8rem;margin-top:0.5rem;}}
.btn{{flex:1;background:var(--pink);color:white;border:4px solid var(--navy);box-shadow:4px 4px 0 var(--navy);padding:0.8rem;font-family:'Press Start 2P',monospace;font-size:0.6rem;cursor:pointer;display:none;}}
.btn:hover{{transform:translate(-2px,-2px);box-shadow:6px 6px 0 var(--navy);}}
.result-card{{background:var(--cream);border:6px solid var(--navy);box-shadow:8px 8px 0 var(--navy);padding:2rem;text-align:center;display:none;}}
.result-card.show{{display:block;}}
.result-title{{font-family:'Noto Sans KR',sans-serif;font-size:1.2rem;font-weight:900;color:var(--navy);margin-bottom:1rem;}}
.result-score{{font-size:3rem;color:var(--yellow);text-shadow:4px 4px 0 var(--yellow-dark),8px 8px 0 #000;margin-bottom:0.5rem;display:block;}}
.result-total{{font-size:0.5rem;color:var(--navy);margin-bottom:1.5rem;}}
.btn-main{{background:var(--navy);color:var(--yellow);border:4px solid var(--yellow);box-shadow:4px 4px 0 #000;padding:1rem 2rem;font-family:'Noto Sans KR',sans-serif;font-weight:900;font-size:1rem;cursor:pointer;text-decoration:none;display:inline-block;margin-top:1rem;}}
.btn-main:hover{{transform:translate(-2px,-2px);box-shadow:6px 6px 0 #000;}}
.stars{{position:fixed;pointer-events:none;z-index:999;}}
.coin-item{{position:absolute;width:24px;height:24px;background:var(--yellow);border:3px solid var(--yellow-dark);animation:coinUp 0.7s steps(8) forwards;box-shadow:2px 2px 0 #000;display:flex;align-items:center;justify-content:center;}}
.coin-item::before{{content:'₩';font-size:0.55rem;font-weight:900;color:var(--navy);}}
@keyframes coinUp{{0%{{opacity:1;transform:translateY(0)}}100%{{opacity:0;transform:translateY(-100px)}}}}
.score-popup{{position:fixed;font-size:0.7rem;pointer-events:none;z-index:1000;animation:popUp 0.8s steps(8) forwards;}}
@keyframes popUp{{0%{{opacity:1;transform:translateY(0)}}100%{{opacity:0;transform:translateY(-60px)}}}}
</style>
</head>
<body>
<div class="bg"><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div></div>
<div class="wrap content">
  <div class="title-card">
    <div class="title-main">매십문</div>
    <div class="title-sub">DAILY FINANCE QUIZ CHALLENGE</div>
    <div class="date-badge">{{today}}</div>
  </div>
  <div class="progress-wrap">
    <div class="progress-bar" id="progressBar" style="width:0%"></div>
    <div class="progress-label" id="progressLabel">0/10</div>
  </div>
  <div id="quizArea"></div>
  <div class="result-card" id="resultCard">
    <div class="result-title">🎉 오늘의 매십문 완료!</div>
    <span class="result-score" id="resultScore">0</span>
    <div class="result-total">/ 10문제</div>
    <a href="https://mae10moon.com" class="btn-main">매십문에서 더 풀기 ▶</a>
  </div>
</div>
<div class="stars" id="stars"></div>
<script>
var quizzes={{quizzes_json}};
var current=0;var score=0;var answered=false;var audioCtx=null;
function getTagClass(cat){{if(cat==='금융용어')return 'tag-금융용어';if(cat==='시사')return 'tag-시사';if(cat==='세부지식')return 'tag-세부지식';return 'tag-default';}}
function render(){{
  if(current>=quizzes.length){{showResult();return;}}
  var q=quizzes[current];
  document.getElementById('progressBar').style.width=(current/quizzes.length*100)+'%';
  document.getElementById('progressLabel').textContent=current+'/'+quizzes.length;
  var optHtml='';for(var i=0;i<q.options.length;i++)optHtml+='<button class="option" onclick="selectOpt(this,'+i+')">'+q.options[i]+'</button>';
  var expParts=(q.explanation||'').split('[오답해설]');
  var expHtml=expParts.length>1?expParts[0].trim()+'<br><br><strong>[오답해설]</strong><br>'+expParts.slice(1).map(function(p){{return p.trim();}}).join('<br>'):q.explanation||'';
  var newsHtml='';if(q.news_context){{newsHtml='<div class="news-ctx">📰 '+q.news_context;if(q.news_url)newsHtml+=' <a href="'+q.news_url+'" target="_blank" class="news-link">[원문]</a>';newsHtml+='</div>';}}
  document.getElementById('quizArea').innerHTML='<div class="quiz-card"><span class="category-tag '+getTagClass(q.category)+'">'+q.category+'</span><div class="question-text">'+q.question+'</div><div class="options">'+optHtml+'</div><div class="explanation" id="exp"><div class="exp-label">📖 EXPLANATION</div>'+expHtml+newsHtml+'</div></div><div class="nav-buttons"><button class="btn" id="nextBtn" onclick="nextQ()">'+(current===quizzes.length-1?'RESULT ▶':'NEXT ▶')+'</button></div>';
  answered=false;
}}
function selectOpt(el,idx){{
  if(answered)return;answered=true;
  var q=quizzes[current];var opts=document.querySelectorAll('.option');
  var getNum=function(s){{var m=s.match(/[①②③④]/);return m?m[0]:''}};
  var isCorrect=getNum(el.textContent)&&getNum(q.answer)&&getNum(el.textContent)===getNum(q.answer);
  for(var i=0;i<opts.length;i++){{opts[i].disabled=true;if(getNum(opts[i].textContent)===getNum(q.answer))opts[i].classList.add('correct');else if(opts[i]===el&&!isCorrect)opts[i].classList.add('wrong');}}
  if(isCorrect)score++;
  var rect=el.getBoundingClientRect();spawnCoins(rect.left+rect.width/2,rect.top+rect.height/2,isCorrect);showScorePopup(isCorrect);playBeep(isCorrect);
  document.getElementById('exp').classList.add('show');document.getElementById('nextBtn').style.display='block';
}}
function nextQ(){{current++;render();}}
function showResult(){{document.getElementById('quizArea').style.display='none';document.getElementById('progressBar').style.width='100%';document.getElementById('progressLabel').textContent=quizzes.length+'/'+quizzes.length;document.getElementById('resultCard').classList.add('show');document.getElementById('resultScore').textContent=score;}}
function spawnCoins(x,y,correct){{if(!correct)return;var s=document.getElementById('stars');for(var i=0;i<5;i++){{var c=document.createElement('div');c.className='coin-item';c.style.left=(x-12+(Math.random()-0.5)*60)+'px';c.style.top=(y-12)+'px';c.style.animationDelay=(i*0.06)+'s';s.appendChild(c);setTimeout(function(cc){{s.removeChild(cc);}},800,c);}}}}
function showScorePopup(correct){{var p=document.createElement('div');p.className='score-popup';p.style.left='50%';p.style.top='40%';p.style.color=correct?'var(--yellow)':'var(--red)';p.textContent=correct?'+1 !':'MISS!';document.body.appendChild(p);setTimeout(function(){{document.body.removeChild(p);}},800);}}
function playBeep(correct){{try{{if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)();if(audioCtx.state==='suspended')audioCtx.resume();var o=audioCtx.createOscillator();var g=audioCtx.createGain();o.connect(g);g.connect(audioCtx.destination);o.type='square';if(correct){{o.frequency.setValueAtTime(523,audioCtx.currentTime);o.frequency.setValueAtTime(659,audioCtx.currentTime+0.1);o.frequency.setValueAtTime(784,audioCtx.currentTime+0.2);}}else{{o.frequency.setValueAtTime(200,audioCtx.currentTime);o.frequency.setValueAtTime(150,audioCtx.currentTime+0.15);}}g.gain.setValueAtTime(0.15,audioCtx.currentTime);g.gain.exponentialRampToValueAtTime(0.001,audioCtx.currentTime+0.4);o.start(audioCtx.currentTime);o.stop(audioCtx.currentTime+0.4);}}catch(e){{}}}}
document.addEventListener('click',function(){{if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)();if(audioCtx.state==='suspended')audioCtx.resume();}},{{once:true}});
render();
</script>
</body>
</html>"""

# === 5. GitHub 파일 푸시 ===
def github_push(path, content, message):
    url = f'https://api.github.com/repos/{{GITHUB_OWNER}}/{{GITHUB_REPO}}/contents/{{path}}'
    headers = {{'Authorization': f'token {{GITHUB_TOKEN}}', 'Accept': 'application/vnd.github.v3+json'}}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    data = {{'message': message, 'content': base64.b64encode(content.encode('utf-8')).decode('utf-8')}}
    if sha:
        data['sha'] = sha
    res = requests.put(url, headers=headers, json=data)
    return res.status_code in [200, 201]

result = github_push(f'quiz/{{today}}.html', html, f'Add quiz {{today}}')
print(f"quiz HTML 푸시: {{'성공' if result else '실패'}}")

# === 6. sitemap 업데이트 ===
res = requests.get(
    f'{{SUPABASE_URL}}/rest/v1/Quiz?select=date&order=date.desc',
    headers={{**headers, 'Prefer': 'return=representation'}},
    params={{'limit': 1000}}
)
all_dates = list(set([r['date'] for r in res.json()])) if res.status_code == 200 else [today]
all_dates.sort(reverse=True)

urls_xml = '\n'.join([f"""  <url>
    <loc>https://mae10moon.com/quiz/{{d}}.html</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""" for d in all_dates])

sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://mae10moon.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
  <url><loc>https://mae10moon.com/news.html</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://mae10moon.com/about.html</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>
  <url><loc>https://mae10moon.com/contact.html</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://mae10moon.com/privacy.html</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>
{{urls_xml}}
</urlset>"""

result = github_push('sitemap.xml', sitemap, f'Update sitemap {{today}}')
print(f"sitemap 푸시: {{'성공' if result else '실패'}}")
print("완료!")
