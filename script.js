const leaders = [
    { name: '줄리어스 시저', img: 'images/caesar.jpg' },
    { name: '클레오파트라', img: 'images/cleopatra.jpg' },
    { name: '칭기즈 칸', img: 'images/genghis_khan.jpg' },
    { name: '잔 다르크', img: 'images/joan_of_arc.jpg' },
    { name: '엘리자베스 1세', img: 'images/elizabeth_i.jpg' },
    { name: '나폴레옹 보나파르트', img: 'images/napoleon.jpg' },
    { name: '에이브러햄 링컨', img: 'images/lincoln.jpg' },
    { name: '윈스턴 처칠', img: 'images/churchill.jpg' }
];

let currentRound = leaders.slice(); // 현재 라운드 후보
let nextRound = []; // 다음 라운드 진출자
let matchIndex = 0; // 현재 대결 인덱스

const candidate1Elem = document.getElementById('candidate-1');
const candidate2Elem = document.getElementById('candidate-2');
const roundTitleElem = document.getElementById('round-title');
const worldCupElem = document.querySelector('.world-cup');
const winnerSectionElem = document.getElementById('winner-section');

function updateCandidates() {
    if (matchIndex >= currentRound.length / 2) {
        // 현재 라운드 종료, 다음 라운드로 이동
        currentRound = nextRound.slice();
        nextRound = [];
        matchIndex = 0;

        // 라운드 타이틀 업데이트
        const round = currentRound.length;
        if (round > 1) {
            roundTitleElem.textContent = `${round}강`;
        } else {
            // 최종 우승자 표시
            worldCupElem.style.display = 'none';
            roundTitleElem.style.display = 'none';
            
            const winner = currentRound[0];
            document.getElementById('winner-img').src = winner.img;
            document.getElementById('winner-name').textContent = winner.name;
            winnerSectionElem.style.display = 'block';
            return;
        }
    }

    const candidate1 = currentRound[matchIndex * 2];
    const candidate2 = currentRound[matchIndex * 2 + 1];

    candidate1Elem.querySelector('img').src = candidate1.img;
    candidate1Elem.querySelector('img').alt = candidate1.name;
    candidate1Elem.querySelector('p').textContent = candidate1.name;

    candidate2Elem.querySelector('img').src = candidate2.img;
    candidate2Elem.querySelector('img').alt = candidate2.name;
    candidate2Elem.querySelector('p').textContent = candidate2.name;
}

function selectCandidate(selectedIndex) {
    const winner = currentRound[matchIndex * 2 + selectedIndex];
    nextRound.push(winner);
    matchIndex++;
    updateCandidates();
}

candidate1Elem.addEventListener('click', () => selectCandidate(0));
candidate2Elem.addEventListener('click', () => selectCandidate(1));

// 초기화
leaders.sort(() => Math.random() - 0.5); // 후보 섞기
updateCandidates();
