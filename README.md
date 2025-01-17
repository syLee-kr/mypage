개인 페이지 작업 프로젝트
홈페이지 주소 - http://aries.kr


fast api를 사용한 간단한 개인 페이지 프로젝트 2025.01.06 ~

목표 - 굿즈 판매와 게시글을 올리고, 사용자와 1대 1로 소통하는 개인 페이지 제작.

아키텍처 구조 -- 비동기 - mongoDB > 일반 로직.  동기 - SQL (postgresql, mysql 中 택1) > 결재 로직.
기본적으로 RabbitMQ를 통해 두 DB의 데이터를 동기화 시켜 백업의 역할을 서로 수행함과 동시에, 비즈니스 로직과 일반 로직으로 용도를 구분하여 서버를 구현하는 것이 목표. 

25.01.17 기준 버전 1(비동기 - mongoDB, 웹소켓을 사용한 채팅[채팅, 이미지, 간단한 그림 전송 가능]기능, 게시판과 일정 캘린더) 배포 완료

배포 -- docker -> lightsail 

25.01.17 기준 미구현 기능

- 아이디 비밀번호 찾기
- 알림
- 마켓
- rabbitMQ를 통한 DB 연동
- 로그인
- 설정 (다크모드, 라이트모드)
- 게시물에서 관리자(본인) 프로필 클릭시 관리자 프로필로 이동
