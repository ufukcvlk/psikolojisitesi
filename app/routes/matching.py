# app/routes/matching.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from datetime import datetime
from datetime import date
import os
from fpdf import FPDF
from io import BytesIO
from app.models.psychologist import Psychologist
from app.forms.matching_form import TherapistMatchingForm
from app.services.psychologist_service import PsychologistService

matching_bp = Blueprint('matching', __name__, url_prefix='/matching')

# Soru metinleri ve form alanları eşleştirmesi
STEP_QUESTIONS = {
    1: {'question': "Have you received psychological support before?", 'field': 'previous_support'},
    2: {'question': "What kind of psychological support did you receive?", 'field': 'previous_support_type'},
    3: {'question': "What approach-based psychotherapy support did you receive?", 'field': 'psychotherapy_approach'},
    4: {'question': "What is the frequency/number of sessions per month?", 'field': 'session_frequency'},
    5: {'question': "Could you briefly explain your reason for seeking therapy?", 'field': 'reason'},
    6: {'question': "What kind of psychological support are you looking for?", 'field': 'support_type'},
    7: {'question': "Which of the following would you like to see improvement in through psychological support?", 'field': 'improvement_areas'},
    8: {'question': "Would you like to provide information about the type of medications and duration of use?", 'field': 'medication_info'},
    9: {'question': "Are you currently on medication?", 'field': 'medication_continues'},
    10: {'question': "Do you have sleep/appetite problems?", 'field': 'sleep_appetite'},
    11: {'question': "How long have you been together?", 'field': 'been_together_years'},
    12: {'question': "Which of the following would you like to see improvement in regarding your relationship by seeking support?", 'field': 'togetherness_improvement_areas'},
    13: {'question': "Number of children?", 'field': 'number_of_children'},
    14: {'question': "Child's age?", 'field': 'age_of_children'},
    15: {'question': "Which of the following would you like to see improvement in for your child?", 'field': 'children_improvement_areas'},
}

# Öneri şablonları
SUGGESTION_TEMPLATES = {
    "Couples Therapy": {
        "Communication problems": [
            "Use effective listening skills.",
            "Try to empathize and understand your partner.",
            "Use 'I language' and avoid accusatory statements.",
            "Implement a weekly 'communication hour' (for sharing feelings and thoughts only).",
            "Use the 'time-out' technique during arguments (take a 20-minute break when emotions run high)."
        ],
        "Extended family problems": [
            "Clarify the couple's own boundaries (defining a private space).",
            "Develop a common stance against family interference.",
            "Agree on matters like vacations, visits, and care in advance.",
            "Create rituals to strengthen the 'we' perception in the relationship."
        ],
        "Disagreements in child/pet care": [
            "Create a responsibility chart (weekly plan).",
            "Determine common values and priorities in decision-making processes.",
            "Find solutions that center on the needs of the child/animal sharing the home.",
            "Plan for external support to ease the care burden (nanny, daycare, vet)."
        ],
        "Financial problems": [
            "Use a joint budget book or app.",
            "Prepare a list of spending priorities.",
            "Make major financial decisions together (house, car, loan).",
            "Discuss money issues with a solution-oriented approach, not a blaming one."
        ],
        "Lack of social sharing/activities": [
            "Make a list of shared hobbies and create a monthly plan.",
            "Adopt the 'one new experience a month' rule (new restaurant, event, sport, etc.).",
            "Set aside at least one day a week for 'couple time'.",
            "Arrange joint gatherings with friends to expand social support networks."
        ],
        "Lack of romantic interest/affection": [
            "Make small daily gestures (leaving notes, compliments).",
            "Increase the frequency of physical touch (hugging, holding hands).",
            "Create a shared romantic memory (weekly mini-surprise).",
            "Discover and act on each other's love languages (gifts, service, touch, etc.)."
        ],
        "Cheating/Infidelity": [
            "First, prepare a plan to rebuild emotional trust.",
            "Provide a safe space for expressing feelings.",
            "Review the relationship contract.",
            "Seek individual/couples therapy support if needed.",
            "Make a joint decision (to separate/continue)."
        ],
        "Lack of sexual desire": [
            "Create an open and non-judgmental environment for talking about sex.",
            "Get physical health and hormone levels checked.",
            "Increase emotional intimacy in the relationship."
        ],
        "Differences in future expectations": [
            "Openly discuss long-term goals (children, city, career).",
            "Create a joint 'dream map'.",
            "Learn to see differences as a source of richness, not conflict.",
            "Break down decision-making processes into small steps."
        ]
    },
    "Child & Adolescent Therapy": {
        "Emotion regulation": [
            "Work on naming emotions (e.g., 'What are you feeling right now?' cards).",
            "Practice breathing, relaxation, and mindfulness exercises.",
            "Use the 'emotion thermometer' method (measuring intensity on a scale of 0–10).",
            "Create a coping box for negative emotions (music, drawing, games)."
        ],
        "Social anxiety/withdrawal": [
            "Use gradual exposure (first small groups, then larger crowds).",
            "Practice social skills through role-playing.",
            "Set small daily social goals.",
            "Reinforce positive social experiences."
        ],
        "School/Exam anxiety": [
            "Create a time management plan.",
            "Teach relaxation techniques for before exams.",
            "Set realistic goals and progress in stages.",
            "Question the belief that 'success = worth'."
        ],
        "Peer bullying (perpetrating, being exposed)": [
            "Clarify the definition and consequences of bullying.",
            "Teach mechanisms for seeking support from a trusted adult.",
            "Work on developing empathy.",
            "Practice boundary-setting and the ability to say no."
        ],
        "Adolescent emotional ups and downs": [
            "Normalize emotions.",
            "Increase ways of self-expression (writing, art, sports).",
            "Establish a routine (sleep, nutrition, social time).",
            "Keep an emotion journal."
        ],
        "Difficulty in relationship with authority": [
            "Teach respectful communication skills.",
            "Work on balancing 'demanding rights' with 'respect'.",
            "Explain the reasons behind family rules.",
            "Improve negotiation skills."
        ],
        "Boundary violations": [
            "Teach the concept of personal space.",
            "Set natural consequences when rules are not followed.",
            "Practice boundary-setting dialogues through role-playing.",
            "Clarify the balance between rights and responsibilities."
        ]
    },
    "Individual Therapy": {
        "Negative thoughts": [
            "Gain conscious awareness through the thought-feeling-behavior triangle.",
            "Create an automatic thoughts journal.",
            "Work on restructuring cognitive distortions through examples.",
            "Use 'evidence vs. counter-evidence' questioning techniques.",
            "Practice thought defusion techniques (ACT: 'I have this thought, but I am not this thought')."
        ],
        "Depressive feelings": [
            "Set mini-goals to increase daily functioning (5-minute walk, taking a shower, opening a window).",
            "Create a list of enjoyable activities and a behavioral activation plan.",
            "Question feelings of hopelessness and self-worth.",
            "Develop insight through an emotion journal.",
            "Encourage social connections (one message, call, or short meeting)."
        ],
        "Anxiety/Panic/Worry": [
            "Plan for gradual exposure using an anxiety pyramid.",
            "Cope with physical symptoms: diaphragmatic breathing, relaxation exercises.",
            "Recognize the 'catastrophizing' distortion and produce alternative thoughts.",
            "Keep an anxiety journal and perform a reality check on the 'worst-case scenario'.",
            "Work on 'things I can and cannot control'."
        ],
        "Sleep/Appetite problems": [
            "Sleep hygiene education (screen time, caffeine, pre-sleep routine).",
            "Mind-dumping journal (writing down thoughts before sleep).",
            "Track daily meals to analyze appetite and mood.",
            "Gain awareness of emotional triggers for eating behaviors.",
            "Stimulus control (the bed should only be used for sleep and rest)."
        ],
        "Anger management": [
            "Develop skills to regulate and express anger without suppressing it.",
            "Anger journal: analyze triggers, thoughts, behaviors, and consequences.",
            "Identify underlying needs for emotions (compassion, being seen, respect).",
            "Physical regulation strategies: time-out, cooling-off period, breathing exercises.",
            "Alternative ways of expression: 'I am very angry right now, but I'm learning how to deal with it'."
        ],
        "Romantic relationships": [
            "Work on insights into relationship schemas (abandonment, worthlessness, etc.).",
            "Recognize relationship language/attachment style.",
            "Work on setting boundaries and balancing 'selfhood' with 'we-ness'.",
            "Recognize and restructure repetitive relationship cycles.",
            "Develop skills for open and needs-based communication with a partner."
        ],
        "Family relationships": [
            "Recognize family roles and patterns (healthy and unhealthy aspects).",
            "Work on the current effects of childhood dynamics with parents.",
            "Develop emotional boundaries and individuation skills.",
            "Separate feelings of guilt from boundaries of responsibility.",
            "Raise awareness of intergenerational transmissions."
        ],
        "Socialization/Friendship relationships": [
            "Social skills training (assertiveness, keeping a conversation going, eye contact).",
            "Enter social settings through gradual exposure.",
            "Exercises for setting boundaries and saying no in relationships.",
            "Evaluate existing relationships based on levels of closeness, trust, and equality.",
            "Set goals for exploring new social areas (club, class, volunteering, etc.)."
        ],
        "Work performance/Work relationships": [
            "Work on time management and task prioritization.",
            "Reality-test performance anxiety and question the definition of success.",
            "Set boundaries at work, separating professional identity (work-self) from personal identity (self).",
            "Address relationships with authority figures.",
            "Raise awareness of burnout symptoms and plan for breaks."
        ],
        "Feeling of loneliness": [
            "Work on the difference between loneliness and being alone.",
            "Shift the concept from 'quantity' to 'quality'.",
            "Develop individual activities that increase relational satisfaction.",
            "Learn to identify emotional needs and share them with the outside world.",
            "Practice self-compassion during moments of loneliness (letter, talking to a mirror)."
        ],
        "Lack of belonging": [
            "Recognize identity domains (sexual orientation, ethnic identity, beliefs, culture, etc.).",
            "Create a map of safe spaces and reliable relationships.",
            "Develop internal resources and coping strategies."
        ]
    },
    "Anxiety": [
        "Cognitive behavioral techniques to reduce your anxiety levels are recommended."
    ],
    "Depression": [
        "Therapy and lifestyle changes to improve your mood may be beneficial."
    ],
    "Sleep": [
        "Sleep hygiene education and relaxation exercises are recommended."
    ],
    "Relationship": [
        "Sessions to strengthen your relationship skills are recommended."
    ]
}

# Adımlar arası geçiş mantığı
STEP_FLOW = {
    1: {'Yes': 2, 'No': 6},
    2: {'Psychotherapy': 3, 'Medication treatment': 8},
    3: 4,
    4: 5,
    5: 6,
    6: {'Individual Therapy': 7, 'Child & Adolescent Therapy': 13, 'Couples Therapy': 11},
    7: 'results',
    8: 9,
    9: {'Yes': 10, 'No': 6},
    10: 6,
    11: 12,
    12: 'results',
    13: 14,
    14: 15,
    15: 'results'
}

def _normalize_step_input(step_value):
    """Gelen step parametresini tamsayıya çevirir."""
    if step_value:
        try:
            return int(step_value)
        except (ValueError, TypeError):
            return 1 # Geçersiz bir step değeri varsa 1'e dön
    return 1

@matching_bp.route('/', methods=['GET', 'POST'])
def find_therapist():
    form = TherapistMatchingForm()
    
    # Oturumda mevcut bir adım yoksa veya sıfırlama isteği varsa oturumu başlat
    if 'current_step' not in session or request.args.get('reset'):
        session['current_step'] = 1
        session['matching_answers'] = {}

    has_progress = False

    # POST isteği
    if request.method == 'POST':
        posted_step = _normalize_step_input(request.form.get('step'))
        
        history = session.get('step_history', [])
        if not history or history[-1] != posted_step:
            history.append(posted_step)
            session['step_history'] = history
        
        answers = session.get('matching_answers', {})
        field_name = STEP_QUESTIONS.get(posted_step, {}).get('field')

        if not field_name:
            flash('Invalid step or form field.', 'danger')
            return redirect(url_for('matching.find_therapist', step=session.get('current_step', 1)))

        if field_name == 'improvement_areas':
            stored_value = request.form.getlist(field_name)
            if len(stored_value) > 3:
                flash('You can make up to 3 selections.', 'danger')
                return redirect(url_for('matching.find_therapist', step=posted_step))
        elif field_name == 'togetherness_improvement_areas':
            stored_value = request.form.getlist(field_name)
            if len(stored_value) > 3:
                flash('You can make up to 3 selections.', 'danger')
                return redirect(url_for('matching.find_therapist', step=posted_step))
        elif field_name == 'children_improvement_areas':
            stored_value = request.form.getlist(field_name)
            if len(stored_value) > 3:
                flash('You can make up to 3 selections.', 'danger')
                return redirect(url_for('matching.find_therapist', step=posted_step))
        elif field_name in ['reason', 'medication_info']:
            stored_value = request.form.get(field_name, '').strip()
        else:
            stored_value = request.form.get(field_name, '')
            
        answers[str(posted_step)] = stored_value
        session['matching_answers'] = answers
        
        next_step_logic = STEP_FLOW.get(posted_step)
        if isinstance(next_step_logic, dict):
            first_answer = stored_value[0] if isinstance(stored_value, list) else stored_value
            next_step = next_step_logic.get(first_answer)
        else:
            next_step = next_step_logic

        if next_step == 'results':
            if not current_user.is_authenticated:
                session['pending_show_results'] = True
                flash("Please log in or register to see suitable therapist recommendations.", "warning")
                return redirect(url_for('auth.login'))
            return redirect(url_for('matching.results'))
        
        if isinstance(next_step, int):
            session['current_step'] = next_step
        return redirect(url_for('matching.find_therapist', step=next_step))

    # GET isteği
    current_step = _normalize_step_input(request.values.get('step')) if 'step' in request.args else session.get('current_step', 1)
    
    # Ana sayfaya gelindiğinde (step parametresi olmadan) ve devam eden bir oturum varsa modal gösterilir.
    if not request.args.get('step') and session.get('current_step', 1) > 1:
        has_progress = True
        current_step = session.get('current_step', 1)
    else:
        session['current_step'] = current_step
    
    return render_template(
        'matching/form.html',
        form=form,
        step=current_step,
        has_progress=has_progress,
        resume_step=session.get('current_step', 1),
        answers=session.get('matching_answers', {})
    )

@matching_bp.route('/back')
def go_back():
    """Kullanıcıyı bir önceki mantıksal adıma yönlendirir."""
    history = session.get('step_history', [])
    
    if history:
        previous_step = history.pop()
        session['step_history'] = history  # Güncellenmiş listeyi kaydet
        session['current_step'] = previous_step # Mevcut adımı da güncelle
        return redirect(url_for('matching.find_therapist', step=previous_step))
        
    # Geçmiş boşsa ilk adıma yönlendir
    return redirect(url_for('matching.find_therapist', step=1))

@matching_bp.route('/reset')
def reset():
    session.pop('matching_answers', None)
    session.pop('current_step', None)
    session.pop('recommended_therapist_id', None)
    return redirect(url_for('matching.find_therapist', step=1))

@matching_bp.route('/results')
@login_required
def results():
    answers = session.get('matching_answers', {})
    specialties = []
    support_type = answers.get('6')

    if support_type == 'Individual Therapy':
        specialties.extend(answers.get('7', []))
    elif support_type == 'Couples Therapy':
        specialties.extend(answers.get('12', []))
    elif support_type == 'Child & Adolescent Therapy':
        specialties.extend(answers.get('15', []))

    if support_type:
        specialties.append(support_type)

    if not specialties:
        # Öneri bulunamazsa, oturumdaki öneri ID'sini temizle
        session.pop('recommended_therapist_id', None)
        return render_template('matching/results.html', recommendation=None, therapists=[], answers=answers)

    matching_psychologists = set()
    for specialty in specialties:
        found_psychologists = PsychologistService.filter_by_specialty(specialty)
        for psy in found_psychologists:
            matching_psychologists.add(psy)
    
    therapists = list(matching_psychologists)
    
    if not therapists:
        # Öneri bulunamazsa, oturumdaki öneri ID'sini temizle
        session.pop('recommended_therapist_id', None)
        return render_template('matching/results.html', recommendation=None, therapists=[], answers=answers)

    # Terapistleri ortalama puana göre sırala
    therapists.sort(key=lambda p: p.average_rating if p.average_rating is not None else -1, reverse=True)
    
    recommendation = therapists.pop(0) if therapists else None
    
    # Yeni eklenen kısım: Önerilen terapistin ID'sini oturuma kaydet
    if recommendation:
        session['recommended_therapist_id'] = recommendation.id
    else:
        session.pop('recommended_therapist_id', None)
    
    # Her terapist nesnesine yıldız derecelendirmesini ekleyin
    # Not: Buradaki yıldızlar HTML sayfasında gösterilecek, PDF'te değil.
    def get_star_rating_for_html(rating, max_stars=5):
        if rating is None or rating == 0:
            return '☆☆☆☆☆'
        
        full_star = '★'
        half_star = '½'
        empty_star = '☆'
        
        rounded_rating = round(rating * 2) / 2
        full_stars = int(rounded_rating)
        half_stars = 1 if rounded_rating - full_stars > 0 else 0
        empty_stars = max_stars - full_stars - half_stars
        
        return (full_star * full_stars) + (half_star * half_stars) + (empty_star * empty_stars)
        
    if recommendation:
        recommendation.stars = get_star_rating_for_html(recommendation.average_rating)        

    for t in therapists:
        t.stars = get_star_rating_for_html(t.average_rating)
    
    return render_template('matching/results.html', therapists=therapists, answers=answers, recommendation=recommendation)

@matching_bp.route('/generate_report')
@login_required
def generate_report():
    def wrap_long_words(text, max_len=40):
        words = text.split()
        result = []
        for word in words:
            if len(word) > max_len:
                chunks = [word[i:i+max_len] for i in range(0, len(word), max_len)]
                result.append("-\n".join(chunks))
            else:
                result.append(word)
        return " ".join(result)

    class PDF(FPDF):
        def header(self):
            logo_path = os.path.join(current_app.static_folder, 'images', 'arkaplan.jpg')
            if os.path.exists(logo_path):
                self.image(logo_path, x=10, y=8, w=30)
            self.set_font("NotoSans", 'B', 14)
            self.cell(0, 10, "ModeCalm - Evaluation Report", ln=True, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('helvetica', 'I', 8)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", 0, 0, 'C')

    # Bu fonksiyon sadece PDF için sayısal puan döndürür.
    def get_rating_as_text(rating, max_stars=5):
        if rating is None or rating == 0:
            return 'No reviews'
        rounded_rating = round(rating * 2) / 2
        return f"{rounded_rating} / {max_stars}"

    def add_therapist_to_pdf(pdf, therapist, is_recommended=False):
        """PDF'e tek bir terapist bilgisini biçimlendirilmiş şekilde ekler."""
        # Tahmini yükseklik (görsel + metinler için minimum)
        image_box_height = 40
        min_height = 50 
        
        # Sayfa sonunda yeterli boşluk yoksa yeni sayfa ekle
        if pdf.get_y() + min_height > pdf.page_break_trigger:
            pdf.add_page()
            
        start_y = pdf.get_y()
        
        image_box_width = 40
        text_start_x = pdf.l_margin + image_box_width + 5
        text_start_y = start_y + 5
        
        # Kutuyu çiz
        if is_recommended:
            pdf.set_fill_color(240, 255, 240)
        else:
            pdf.set_draw_color(200, 200, 200)

        # Görseli yerleştirin
        if therapist.profile_image_url:
            image_path = os.path.join(current_app.static_folder, 'images', therapist.profile_image_url.lstrip('/\\'))
            if os.path.exists(image_path):
                pdf.image(image_path, x=pdf.l_margin + 2, y=start_y + 2, w=image_box_width - 4, h=image_box_height - 4)

        # Metinleri yerleştirin
        pdf.set_xy(text_start_x, text_start_y)
        pdf.set_font("NotoSans", 'B', 12)
        pdf.cell(0, 7, therapist.full_name, ln=True)

        pdf.set_x(text_start_x)
        pdf.set_font("NotoSans", '', 11)
        rating_text = get_rating_as_text(therapist.average_rating)
        pdf.cell(0, 7, f"Average Score: {rating_text}", ln=True)

        pdf.set_x(text_start_x)
        pdf.set_font("NotoSans", '', 10)
        specialties_str = ", ".join(therapist.get_specialties())
        pdf.multi_cell(pdf.w - text_start_x - pdf.r_margin, 5, f"Areas of Expertise: {specialties_str}")
        
        # Metin bloğunun bittiği son Y pozisyonunu alın
        end_y_text = pdf.get_y()
        
        # Görselin bittiği pozisyonu hesaplayın
        end_y_image = start_y + image_box_height + 5  # Görsel ve tampon boşluk
        
        # Bir sonraki bloğun başlayacağı konumu, görsel ve metin bloğundan hangisi daha yüksekse ona göre ayarlayın
        next_y = max(end_y_text, end_y_image)
        
        # Kutuyu son yüksekliğe göre yeniden çiz
        if is_recommended:
            pdf.rect(pdf.l_margin, start_y, pdf.w - pdf.l_margin - pdf.r_margin, next_y - start_y, 'DF')
        else:
            pdf.rect(pdf.l_margin, start_y, pdf.w - pdf.l_margin - pdf.r_margin, next_y - start_y, 'D')
            
        # Metinleri ve görseli tekrar üzerine yazma (ilk deneme sırasında çizilen kutuyu örtmek için)
        if therapist.profile_image_url:
            if os.path.exists(image_path):
                pdf.image(image_path, x=pdf.l_margin + 2, y=start_y + 2, w=image_box_width - 4, h=image_box_height - 4)
        pdf.set_xy(text_start_x, text_start_y)
        pdf.set_font("NotoSans", 'B', 12)
        pdf.cell(0, 7, therapist.full_name, ln=True)
        pdf.set_x(text_start_x)
        pdf.set_font("NotoSans", '', 11)
        pdf.cell(0, 7, f"Average Score: {rating_text}", ln=True)
        pdf.set_x(text_start_x)
        pdf.set_font("NotoSans", '', 10)
        pdf.multi_cell(pdf.w - text_start_x - pdf.r_margin, 5, f"Areas of Expertise: {specialties_str}")
        
        # Bir sonraki eleman için Y pozisyonunu ayarlayın
        pdf.set_y(next_y + 5)
    pdf = PDF()
    pdf.alias_nb_pages()

    font_regular = os.path.join(current_app.static_folder, "fonts", "NotoSans-Regular.ttf")
    font_bold = os.path.join(current_app.static_folder, "fonts", "NotoSans-Bold.ttf")

    if os.path.exists(font_regular) and os.path.exists(font_bold):
        pdf.add_font("NotoSans", "", font_regular, uni=True)
        pdf.add_font("NotoSans", "B", font_bold, uni=True)
    else:
        pdf.set_font('Helvetica', '', 10)

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    user_label = getattr(current_user, 'full_name', 'Guest')
    report_date = date.today().strftime("%d/%m/%Y")
    
    pdf.set_font("NotoSans", 'B', 12)
    pdf.cell(0, 8, f"User: {user_label}", ln=True)
    pdf.cell(0, 8, f"Report Date: {report_date}", ln=True)
    pdf.ln(5)

    answers = session.get('matching_answers', {})
    
    recommendation = None
    other_therapists = []
    
    # Oturumda kaydedilen ID varsa, önerilen terapisti bul
    recommended_therapist_id = session.get('recommended_therapist_id')
    if recommended_therapist_id:
        recommendation = PsychologistService.get_psychologist_by_id(recommended_therapist_id)

    # Diğer terapistleri bulma mantığı
    specialties = []
    support_type = answers.get('6')
    if support_type == 'Individual Therapy':
        specialties.extend(answers.get('7', []))
    elif support_type == 'Couples Therapy':
        specialties.extend(answers.get('12', []))
    elif support_type == 'Child & Adolescent Therapy':
        specialties.extend(answers.get('15', []))
    if support_type:
        specialties.append(support_type)

    if specialties:
        all_matching_psychologists = set()
        for specialty in specialties:
            found_psychologists = PsychologistService.filter_by_specialty(specialty)
            for psy in found_psychologists:
                all_matching_psychologists.add(psy)
        
        # Önerilen terapisti listeden çıkar
        if recommendation and recommendation in all_matching_psychologists:
            all_matching_psychologists.remove(recommendation)
        
        therapists_list = list(all_matching_psychologists)
        if therapists_list:
            therapists_list.sort(key=lambda p: p.average_rating if p.average_rating is not None else -1, reverse=True)
            other_therapists = therapists_list

    pdf.set_font('NotoSans', 'B', 12)
    pdf.cell(0, 10, "Your answers:", ln=True)
    pdf.ln(2)

    answers = session.get('matching_answers', {})
    
    # answers sözlüğünde yer alan adımlar üzerinden döngü kur
    for step_num_str in sorted(answers.keys(), key=int):
        step_num = int(step_num_str)
        
        # Soru metnini STEP_QUESTIONS sözlüğünden al
        question_data = STEP_QUESTIONS.get(step_num)
        if not question_data:
            continue  # Eğer soru tanımı yoksa, atla.

        question_text = question_data['question']
        answer = answers.get(step_num_str)
        
        # Cevap formatını düzelt
        if isinstance(answer, list):
            answer = ", ".join(answer)
        answer_text = "—" if not answer or (isinstance(answer, str) and not answer.strip()) else str(answer)
        
        pdf.set_font('NotoSans', 'B', 11)
        pdf.multi_cell(0, 7, f"Question: {question_text}")
        
        pdf.set_x(pdf.l_margin)
        pdf.set_font('NotoSans', '', 11)
        pdf.multi_cell(0, 7, f"Answer: {answer_text}")
        pdf.ln(3)

    pdf.ln(5)
    
    pdf.set_font('NotoSans', 'B', 12)
    pdf.cell(0, 10, "Summary and Evaluation:", ln=True)
    pdf.ln(2)
    
    if support_type == 'Couples Therapy':
        togetherness_improvement_areas = answers.get('12', [])
        therapy_suggestions = SUGGESTION_TEMPLATES.get('Couples Therapy', {})
        for area in togetherness_improvement_areas:
            suggestions = therapy_suggestions.get(area, [])
            if suggestions:
                # Başlık için kalın fontu ve yeni satırı ayarla
                pdf.set_font('NotoSans', 'B', 11)
                pdf.set_x(15)
                pdf.multi_cell(0, 7, f"- {area}:")
                # Öneriler için normal fontu ve girintiyi ayarla
                pdf.set_font('NotoSans', '', 11)
                for suggestion in suggestions:
                    pdf.set_x(25)
                    pdf.multi_cell(0, 7, f"• {suggestion}")
                pdf.ln(2)

    elif support_type == 'Child & Adolescent Therapy':
        children_improvement_areas = answers.get('15', [])
        therapy_suggestions = SUGGESTION_TEMPLATES.get('Child & Adolescent Therapy', {})
        for area in children_improvement_areas:
            suggestions = therapy_suggestions.get(area, [])
            if suggestions:
                # Başlık için kalın fontu ve yeni satırı ayarla
                pdf.set_font('NotoSans', 'B', 11)
                pdf.set_x(15)
                pdf.multi_cell(0, 7, f"- {area}:")
                # Öneriler için normal fontu ve girintiyi ayarla
                pdf.set_font('NotoSans', '', 11)
                for suggestion in suggestions:
                    pdf.set_x(25)
                    pdf.multi_cell(0, 7, f"• {suggestion}")
                pdf.ln(2)
    elif support_type == 'Individual Therapy':
        improvement_areas = answers.get('7', [])
        therapy_suggestions = SUGGESTION_TEMPLATES.get('Individual Therapy', {})
        for area in improvement_areas:
            suggestions = therapy_suggestions.get(area, [])
            if suggestions:
                # Başlık için kalın fontu ve yeni satırı ayarla
                pdf.set_font('NotoSans', 'B', 11)
                pdf.set_x(15)
                pdf.multi_cell(0, 7, f"- {area}:")
                # Öneriler için normal fontu ve girintiyi ayarla
                pdf.set_font('NotoSans', '', 11)
                for suggestion in suggestions:
                    pdf.set_x(25)
                    pdf.multi_cell(0, 7, f"• {suggestion}")
                pdf.ln(2)
    else:
        improvement_areas = answers.get('7', [])
        for area in improvement_areas:
            suggestions = SUGGESTION_TEMPLATES.get(area.capitalize(), [])
            if suggestions:
                for suggestion in suggestions:
                    pdf.set_x(15)
                    pdf.multi_cell(0, 7, f"- {suggestion}")
                pdf.ln(2)

    # Hiçbir öneri yoksa genel bir metin göster
    if not any(
        (answers.get('12', []), answers.get('15', []), answers.get('7', []))
    ):
        pdf.set_x(15)
        pdf.multi_cell(0, 7, "- Sessions that will support your general psychological well-being are recommended.")
    
    pdf.ln(3)

    pdf.add_page()
    pdf.set_font('NotoSans', 'B', 14)
    pdf.cell(0, 10, "Therapist Recommendations Special to You", ln=True, align='C')
    pdf.ln(10)

    if recommendation:
        pdf.set_font('NotoSans', 'B', 12)
        pdf.cell(0, 10, "Recommended Therapist", ln=True)
        add_therapist_to_pdf(pdf, recommendation, is_recommended=True)
    
    if other_therapists:
        pdf.set_font('NotoSans', 'B', 12)
        pdf.cell(0, 10, "Other Suitable Therapists", ln=True)
        for therapist in other_therapists:
            add_therapist_to_pdf(pdf, therapist)
            
    if not recommendation and not other_therapists:
        pdf.set_font('NotoSans', '', 11)
        pdf.multi_cell(0, 7, "Based on your answers, no suitable therapists were found for you at this time. Please try again later or expand your criteria.")

    pdf_output = pdf.output(dest='S')
    return send_file(
        BytesIO(pdf_output),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Evaluation_Report_{user_label}.pdf"
    )
