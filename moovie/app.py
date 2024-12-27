from flask import Flask, render_template, request, redirect, url_for, jsonify
import random
import openai
import os
from dotenv import load_dotenv
import re

app = Flask(__name__)

# API 키 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 현재 상영 중인 영화 데이터
movies = [
    {"title": "하얼빈", "year": 2024, "poster": "하얼빈.jpg"},
    {"title": "무파사 라이온킹", "year": 2024, "poster": "무파사 라이온킹.jpg"},
    {"title": "인터스텔라", "year": 2014, "poster": "인터스텔라.jpg"},
    {"title": "소방관", "year": 2023, "poster": "소방관.jpg"},
    {"title": "모아나2", "year": 2024, "poster": "모아나2.jpg"}
]

# 좌석 평점 데이터 (in-memory 저장)
seat_ratings = {}

# 현재 상영 중인 영화관과 상영관 데이터
theaters = {
    "성신여대 CGV": ["1관", "2관", "3관"],
    "청량리 Lotte Cinema": ["1관", "2관"],
    "동대문 Megabox": ["1관", "3관", "4관"]
}

# 영화관별 상영 스케줄 (상영관 정보 추가)
theater_schedules = {
    "하얼빈": {
        "성신여대 CGV": [("10:30", "1관"), ("14:00", "3관"), ("18:00", "5관")],
        "청량리 Lotte Cinema": [("11:00", "2관"), ("15:30", "4관"), ("20:00", "6관")],
        "동대문 Megabox": [("09:30", "1관"), ("13:30", "2관"), ("19:30", "4관")]
    },
    "무파사 라이온킹": {
        "성신여대 CGV": [("12:00", "2관"), ("16:00", "4관"), ("21:00", "6관")],
        "청량리 Lotte Cinema": [("10:30", "1관"), ("14:30", "3관"), ("19:00", "5관")],
        "동대문 Megabox": [("11:30", "2관"), ("15:00", "3관"), ("20:30", "5관")]
    },
    "인터스텔라": {
        "성신여대 CGV": [("09:00", "1관"), ("13:00", "3관"), ("17:30", "5관")],
        "청량리 Lotte Cinema": [("10:00", "2관"), ("14:00", "4관"), ("18:00", "6관")],
        "동대문 Megabox": [("08:30", "1관"), ("12:30", "3관"), ("16:30", "5관")]
    },
    "소방관": {
        "성신여대 CGV": [("11:00", "2관"), ("15:30", "4관"), ("20:00", "6관")],
        "청량리 Lotte Cinema": [("09:00", "1관"), ("13:00", "3관"), ("17:00", "5관")],
        "동대문 Megabox": [("10:00", "2관"), ("14:00", "4관"), ("19:00", "5관")]
    },
    "모아나2": {
        "성신여대 CGV": [("10:00", "1관"), ("14:30", "3관"), ("19:00", "5관")],
        "청량리 Lotte Cinema": [("11:30", "2관"), ("15:30", "4관"), ("20:30", "6관")],
        "동대문 Megabox": [("12:00", "3관"), ("16:00", "5관"), ("21:00", "6관")]
    }
}

# 메인 페이지 - 현재 상영 중인 영화
@app.route("/")
def index():
    return render_template("index.html", movies=movies)

# 상영 스케줄 페이지
@app.route("/schedule/<movie>")
def movie_schedule(movie):
    schedules = theater_schedules.get(movie, {})
    return render_template("schedule.html", movie=movie, schedules=schedules)

# 좌석 선택 페이지
@app.route("/select_seat/<movie>/<theater>/<time>/<hall>", methods=["GET", "POST"])
def select_seat(movie, theater, time, hall):
    if request.method == "POST":
        selected_seat = request.form.get("seat")
        return render_template("booking.html", movie=movie, theater=theater, time=time, hall=hall, seat=selected_seat)
    return render_template("select_seat.html", movie=movie, theater=theater, time=time, hall=hall)

# 영화관 및 상영관 선택 페이지
@app.route("/select_theater", methods=["GET", "POST"])
def select_theater():
    if request.method == "POST":
        theater = request.form["theater"]
        hall = request.form["hall"]
        return redirect(url_for('rate_seat_page', theater=theater, hall=hall))
    return render_template("select_theater.html", theaters=theaters)

# 좌석 평점 부여 페이지 (좌석 선택 후 평점 부여)
@app.route("/rate_seat/<theater>/<hall>", methods=["GET", "POST"])
def rate_seat_page(theater, hall):
    if request.method == "POST":
        seat = request.form["seat"]
        rating = int(request.form["rating"])
        seat_key = f"{theater}-{hall}-{seat}"

        if seat_key not in seat_ratings:
            seat_ratings[seat_key] = []
        seat_ratings[seat_key].append(rating)

        return redirect(url_for('index'))

    return render_template("rate_seat.html", theater=theater, hall=hall)

# 좌석 평점 조회 API (예매 시 확인)
@app.route("/get_rating/<theater>/<hall>/<seat>")
def get_rating(theater, hall, seat):
    seat_key = f"{theater}-{hall}-{seat}"
    ratings = seat_ratings.get(seat_key, [])
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else "평점 없음"
    return jsonify({"seat": seat, "average_rating": avg_rating})


# 좌석 초기 평점 80% 설정
def initialize_seat_ratings():
    total_seats = 50  # 5x10 좌석 기준
    rated_seats = int(total_seats * 0.8)  # 80% 좌석에 평점 부여

    for _ in range(rated_seats):
        row = random.randint(1, 5)
        col = random.randint(1, 10)
        seat = f"{row}{col if col < 10 else '0'}"
        theater = random.choice(list(theaters.keys()))
        hall = random.choice(theaters[theater])

        seat_key = f"{theater}-{hall}-{seat}"
        seat_ratings[seat_key] = [random.randint(3, 5) for _ in range(random.randint(1, 5))]

# 추천 영화 라우트
@app.route('/recommend', methods=['POST'])
def recommend():
    user_input = request.form.get('user_input')
    recommendations = get_recommendations(user_input)

    # 정규식으로 영화 제목 추출 (작은따옴표 또는 큰따옴표 내부)
    match = re.search(r"[\"'](.+?)[\"']", recommendations)

    if match:
        movie_title = match.group(1)  # 영화 제목 추출
    else:
        movie_title = "default"  # 기본 이미지 설정

    # 포스터 경로 설정
    poster_path = url_for('static', filename=movie_title + '.jpg')

    return render_template('recommend.html', user_input = user_input, recommendations=recommendations, poster_path=poster_path)

# GPT 기반 영화 추천 함수
# GPT 기반 영화 추천 (5가지 중에서만 추천)
def get_recommendations(user_input):
    prompt = f"""
    사용자가 다음과 같은 입력을 했습니다: "{user_input}".
    아래 다섯 가지 영화 중에서 가장 적합한 것을 하나 추천해주세요:
    1. 하얼빈
    2. 무파사 라이온킹
    3. 소방관
    4. 인터스텔라
    5. 모아나 2

    사용자가 어떤 입력을 하든 반드시 위 영화 중 하나만 추천하고 그 이유도 함께 간단히 답변하세요.
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You are a movie recommendation assistant who always suggests one of the following movies: 하얼빈, 무파사 라이온킹, 소방관, 인터스텔라, 모아나 2."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.7,
    )

    # 수정된 부분: 'message' 방식으로 결과 추출
    recommendation = response.choices[0].message['content'].strip()
    return recommendation


if __name__ == "__main__":
    app.run(debug=True)
