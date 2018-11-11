# Trollcamp 프로젝트 개요
League of legend(이하 LOL) 게임 API 를 이용하여 게임 유저의 데이터를 쌓은 후 분석하여 서비스한다.<br>
OP.GG 와 비슷한 사이트를 만들되, 차별성은 반드시 둔다.<br>
(참고) http://www.op.gg/summoner/userName=lehends<br>

Fast campus Data Engineering Extension School 1기 Trollcamp팀 <br>
권다정, 신동렬, 이승하, 임종운, 정현주, 한은구 (가나다순, 총 6명) <br>

<br>
<hr/>
<br>

# 데이터 수집 프로세스
LOL 서버에서 제공하는 API를 호출하는데 제한이 있어서 호출시마다 적절한 sleep을 걸어줘야 했다. <br>
python으로 작성했고, 단계별 확인을 위해 jupyter notebook으로 작성하였다.<br>

### (준비) 설정 파일 만들기
```
00_config.ipynb
```
배치 작업시 사용할 설정 정보들을 세팅하여 하나의 batch_config.json 파일로 만든다. <br>
앞으로의 단계들에서 이 설정을 불러서 사용하게 된다.<br>

### (1) 한국 서버의 리그 정보를 다운받아 Tier 정보를 구분하여 특정 등급에 해당하는 leagueId 를 추출한다.
```
01_select_leagues.ipynb
```
Download URL : http://canisback.com/leagueId/league_kr.csv <br>
데이터가 너무 많아서 일단 CHALLENGER 등급만을 대상으로 한다. <br>

### (2) leagues API를 호출하여 각 리그의 상세 정보를 받는다.
```
02_call_leagues_api.ipynb
```
각 리그의 상세 정보에는 리그에 속한 플레이어 목록이 들어있다.(summonerId 기준)
LOL Api : /lol/league/v3/leagues/{leagueId} <br>

### (3) 리그에 속한 플레이어들의 summonerId에 accountId를 매치시킨다.
```
03_find_account_id.ipynb
```
리그에 속한 플레이어 목록(summonerId)을 얻어서 DB에 해당 플레이어 정보가 있는지 확인한다. <br>
DB에서 한번 거르는 이유는 배치때마다 accountId를 얻어오기 위해서 API 요청을 하는 수를 줄이기 위함이다. <br>
DB에 있는 플레이어라면, DB에서 accountId를 가져오고, 없는 플레이어라면 Api를 호출하여 accountId를 알아낸다. <br>
LOL Api : /lol/summoner/v3/summoners/{summonerId} <br>
그렇게 얻어진 플레이어들을 5개의 청크로 나누어 csv 파일로 저장한다. (나눠서 matches, timeline 배치를 돌리기 위함) <br>

### (4) matchlist API를 호출하여 플레이어의 매치(게임) 목록을 받는다.
```
04_call_matchlist_api.ipynb
```
이 작업 부터는 5개의 머신에서 각각 돌린다. <br>
이전 배치에서 DB에 넣어두었던 플레이어라면, 마지막 매치(게임)의 timestamp와 비교하여 그 이후의 매치(게임)들만 가져오고 저장한다.<br>
LOL Api : /lol/match/v3/matchlists/by-account/{accountId} <br>

### (5) 플레이어의 매치(게임) 목록을 돌면서 matches, timeline API를 호출한다.
```
05_call_matches_timelines_api.ipynb
```
matches : 매치(게임) 상세 정보 <br>
timeline : 매치(게임) 시간별 발생 이벤트 <br>
플레이어별로 중복되는 매치와 타임라인이 있을수 있으므로 데이터 존재 여부를 미리 검사하여 중복으로 호출하지 않도록 한다. <br>
LOL Api : /lol/match/v3/matches/{matchId}, /lol/match/v3/timelines/by-match/{matchId} <br>

<br>
<hr/>
<br>

# 데이터 분석
2018.11.10 기획 확정 <br>
조만간 업데이트 예정 <br>
