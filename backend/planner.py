import json
import schemas

class GenerativePlanner:
    def __init__(self):
        # We would initialize OpenAI or Gemini client here.
        # e.g., self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        pass

    def generate_plan(self, project: schemas.ProjectCreate, predicted_visitors: int, success_prob: float):
        # Simulated LLM Call
        # If we had a real LLM, we would construct a prompt like:
        # prompt = f"Generate a festival plan for {project.name} in {project.region} with budget {project.expected_budget}. Expected visitors: {predicted_visitors}"
        # response = self.client.chat.completions.create(model="gpt-4", messages=[{"role": "user", "content": prompt}])
        # return json.loads(response.choices[0].message.content)

        # Mocking the response for the prototype
        target_audience = "20대 및 가족 단위" if project.has_experience else "일반 대중"
        concept = f"{project.region}의 특색을 살린 도심 속 힐링 축제"

        mock_response = {
            "concept": concept,
            "target_audience": target_audience,
            "program_plan": [
                {"time": "10:00 - 12:00", "activity": "개막식 및 지역 특산물 장터 오픈"},
                {"time": "13:00 - 17:00", "activity": "메인 체험 부스 운영 및 버스킹 공연" if project.has_experience else "메인 무대 공연"},
                {"time": "18:00 - 21:00", "activity": "축하 공연 및 불꽃놀이" if project.has_celebrity else "야간 라이트업 전시 및 먹거리 야시장"}
            ],
            "marketing_strategy": {
                "main_channel": "Instagram & 지역 커뮤니티",
                "key_message": f"이번 주말, {project.region}에서 만나는 특별한 하루!",
                "budget_allocation": f"온라인 광고 {int(project.promo_budget * 0.6)}원, 오프라인 홍보 {int(project.promo_budget * 0.4)}원"
            },
            "operational_plan": {
                "staffing": f"운영 요원 {project.staff_count}명, 자원봉사자 {project.volunteer_count}명 적재적소 배치",
                "safety": f"경찰 {project.police_count or 5}명 및 의료진 {project.medical_staff_count or 2}명 상시 대기",
                "facilities": f"이동식 화장실 {project.toilets_count or 10}동 추가 설치 요망"
            },
            "risk_factors": [
                "예상보다 많은 인파가 몰릴 경우 주차장 혼잡 예상. 셔틀버스 증편 고려.",
                f"강수 확률 {project.rain_prob * 100}%에 대비한 우천 시 대피소 및 우의 확보 필요." if project.rain_prob and project.rain_prob > 0.3 else "야외 행사의 경우 기온 변화에 대비한 쉼터 마련."
            ]
        }

        return json.dumps(mock_response)

planner = GenerativePlanner()
