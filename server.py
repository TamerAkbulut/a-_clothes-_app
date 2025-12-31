from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ HATA: GEMINI_API_KEY bulunamadı!")
    exit(1)

# Yeni Gemini API Client
client = genai.Client(api_key=GEMINI_API_KEY)

class ProxyHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        if self.path.startswith('/api/ai'):
            self.handle_ai_agent()
        else:
            super().do_GET()

    def handle_ai_agent(self):
        try:
            params = parse_qs(urlparse(self.path).query)
            temp = params.get('temp', ['20'])[0]
            desc = params.get('description', ['Açık'])[0]
            wind = params.get('wind', ['10'])[0]
            loc = params.get('location', ['Bilinmiyor'])[0]

            print(f"\n🔍 İstek Alındı: {loc}, {temp}°C, {desc}, {wind} km/h")

            prompt = f"""Sen bir moda uzmanısın. {loc} için hava durumu: {temp}°C, {desc}, rüzgar {wind} km/h.

Sabah, öğlen ve akşam için kıyafet önerileri ver. Her biri için:
- short: Kısa başlık
- detail: 3-4 cümlelik detaylı açıklama
- reason: 2-3 cümlelik gerekçe  
- alternatives: 3 alternatif (her biri title ve description içermeli)

SADECE JSON formatında yanıt ver:
{{
    "morning": {{
        "short": "Örnek",
        "detail": "Detaylı açıklama",
        "reason": "Gerekçe",
        "alternatives": [
            {{"title": "Alt 1", "description": "Açıklama 1"}},
            {{"title": "Alt 2", "description": "Açıklama 2"}},
            {{"title": "Alt 3", "description": "Açıklama 3"}}
        ]
    }},
    "afternoon": {{}},
    "evening": {{}}
}}"""

            # Yeni API kullanımı
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            print(f"📥 Ham Yanıt Alındı (İlk 200 karakter): {response.text[:200]}...")
            
            # JSON parse et
            try:
                clean_text = response.text.strip()
                if clean_text.startswith('```'):
                    clean_text = clean_text.split('```')[1]
                    if clean_text.startswith('json'):
                        clean_text = clean_text[4:].strip()
                
                result = json.loads(clean_text)
                print(f"✅ JSON Parse Başarılı!")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Hatası: {e}")
                print(f"⚠️ Fallback JSON kullanılıyor...")
                
                result = {
                    "morning": {
                        "short": "Hafif Kazak ve Kot Pantolon",
                        "detail": f"{loc} için sabah serinliğinde {temp}°C sıcaklıkta pamuklu bir t-shirt üzerine ince bir kazak ideal. Kot pantolon ile kombinlendiğinde hem şık hem rahat bir görünüm elde edilir. Katmanlama sayesinde gün ısındıkça kazağı çıkarabilirsiniz.",
                        "reason": f"Sabah saatlerinde {temp}°C gibi orta sıcaklıklarda katmanlı giyim en iyi termal konforu sağlar. Kazak rüzgardan korur, pamuk nefes alır.",
                        "alternatives": [
                            {"title": "Spor Şık", "description": "Sweatshirt ve jogger pantolon kombinasyonu. Rahat ve modern görünüm için ideal."},
                            {"title": "Klasik Stil", "description": "Gömlek ve chino pantolon. İş toplantıları için uygun profesyonel görünüm."},
                            {"title": "Günlük Rahat", "description": "Polo t-shirt ve kargo pantolon. Günlük aktiviteler için pratik seçim."}
                        ]
                    },
                    "afternoon": {
                        "short": "T-shirt ve Hafif Pantolon",
                        "detail": f"Öğlen güneşi için {temp}°C sıcaklıkta nefes alabilen pamuklu t-shirt tercih edin. Açık renkli chino veya keten pantolon serin tutar. Hafif bir ceket yanınızda bulundurabilirsiniz.",
                        "reason": f"Gün ortası sıcaklık {temp}°C civarında olduğunda hava sirkülasyonu önemli. Pamuk ve keten gibi doğal kumaşlar en iyi seçim.",
                        "alternatives": [
                            {"title": "Yazlık Rahat", "description": "Keten gömlek ve şort. Yaz ayları için ideal serin kombinasyon."},
                            {"title": "Modern Casual", "description": "Grafik t-shirt ve slim pantolon. Günlük şehir gezileri için mükemmel."},
                            {"title": "Aktif Stil", "description": "Tank top ve spor şort. Spor aktiviteleri için uygun nem emici kumaşlar."}
                        ]
                    },
                    "evening": {
                        "short": "Gömlek ve Blazer",
                        "detail": f"Akşam serinliği için {temp}°C sıcaklıkta uzun kollu gömlek ve üzerine blazer ceket ideal. Koyu renkli chino pantolon şıklık katar. Deri ayakkabı ile kombinasyon tamamlanır.",
                        "reason": f"Akşam {temp}°C'ye düşebilir. Katmanlı giyim ve blazer hem şık hem koruyucu. Koyu renkler akşam ortamlarına daha uygun.",
                        "alternatives": [
                            {"title": "Smart Casual", "description": "Kazak ve jean kombinasyonu. Akşam buluşmaları için rahat şıklık."},
                            {"title": "Zarif Minimal", "description": "Boğazlı kazak ve koyu pantolon. Sofistike minimalist görünüm."},
                            {"title": "Rahat Akşam", "description": "Hoodie ve jogger. Günlük akşam aktiviteleri için konforlu seçim."}
                        ]
                    }
                }
            
            # Her zaman dilimi kontrolü
            for period in ['morning', 'afternoon', 'evening']:
                if period not in result:
                    result[period] = {
                        "short": "Standart Kıyafet",
                        "detail": "Bu zaman dilimi için öneriler hazırlanıyor.",
                        "reason": "Hava koşullarına göre en uygun seçim.",
                        "alternatives": [
                            {"title": "Klasik", "description": "Zamansız şık parçalar."},
                            {"title": "Sporty", "description": "Hareket özgürlüğü sunan parçalar."},
                            {"title": "Casual", "description": "Günlük kullanım için rahat stil."}
                        ]
                    }
                
                if 'alternatives' not in result[period] or not result[period]['alternatives']:
                    result[period]['alternatives'] = [
                        {"title": "Klasik Şık", "description": "Zamansız ve şık parçalarla kombinasyon."},
                        {"title": "Spor Rahat", "description": "Aktif yaşam için konforlu seçim."},
                        {"title": "Modern Casual", "description": "Günlük stil sahibi görünüm."}
                    ]
            
            print(f"✅ Tüm Kontroller Tamamlandı - Veri Gönderiliyor")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Kritik Hata: {str(e)}")
            import traceback
            traceback.print_exc()
            self.send_error(500, str(e))

if __name__ == '__main__':
    print("🚀 Agentic Fashion AI Server Başlatıldı!")
    print("📡 URL: http://localhost:8000")
    print("🍌 Gemini 2.5 Flash ile çalışıyor...")
    print("=" * 50)
    server = HTTPServer(('localhost', 8000), ProxyHandler)
    server.serve_forever()