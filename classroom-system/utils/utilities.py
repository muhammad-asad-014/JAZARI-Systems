import os
from deepface import DeepFace
os.environ['DEEPFACE_HOME'] = os.path.abspath('./models')
from flask import flash
import socketio


def getImageEmbedding(imgPath):
    """"Generates embedding of image"""
    model_frontend = 'ArcFace'
    model_backend = 'retinaface'
    embedding = DeepFace.represent(img_path = imgPath, model_name = model_frontend, detector_backend = model_backend)
    return embedding




def find_faces(img, embeddings):
    print('Detecting faces in the frame')
    test = DeepFace.represent(img_path = img, model_name ='ArcFace', detector_backend = 'retinaface', enforce_detection=False)
    found = []
    print('Now recognizing the faces.')
    for unknown in test:
        for person in embeddings:
            result = DeepFace.verify(unknown['embedding'], person['Embedding'], model_name = 'ArcFace', detector_backend = 'retinaface', distance_metric = 'cosine', threshold=0.6)
            if result['verified'] == True:
                found.append(person['id'])
    print('following faces found\n', found)
    return found




def text_extractor(file_path):
    from langchain_community.document_loaders import PyMuPDFLoader
    loader = PyMuPDFLoader(file_path)
    print('loading file')
    docs = loader.load()
    print('extracetd text')
    txt = ""
    for doc in docs:
        txt += doc.page_content
    os.remove(file_path)
    print('removed file ')
    return txt

def shuffler_verify(json_txt):
    import json
    import random
    print('loading json')
    txt_list = json.loads(json_txt)
    print('shuffling')
    random.shuffle(txt_list)
    print('dumping')
    if json.dumps(txt_list):
        return True
    else:
        return False


def quiz_generator(api_key,difficulty, count, model = 'openai/gpt-oss-20b:free', quiz_topics = None, quiz_doc = None):
    from openai import OpenAI
    userTxt = quiz_topics
    if quiz_doc:
        print('going for text extraction')
        userTxt = text_extractor(quiz_doc)
    client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key= api_key,
    )

# API call with reasoning
    try:
        print('calling api')
        response = client.chat.completions.create(
        model=model,
        messages=[
    {
        "role": "system",
        "content": f"""
        You are a quiz generator. Based on the following text, create exactly {count} multiple-choice questions at a {difficulty} difficulty level.

        Output ONLY valid JSON in this exact format:
        [
            {{
                "question": "Example Question?",
                "options": [
                    {{ "text": "Option 1", "rationale": "Why incorrect", "correct": false }},
                    {{ "text": "Option 2", "rationale": "Why correct", "correct": true }},
                    {{ "text": "Option 3", "rationale": "...", "correct": false }},
                    {{ "text": "Option 4", "rationale": "...", "correct": false }}
                ]
            }}
        ]

        Rules:
        - Generate exactly {count} questions.
        - Difficulty level must be: {difficulty}.
        - Each question must have 4 options.
        - Each answer must be at a different index/order for each question.
        - Use LaTeX for mathematical formulas (e.g., \\(x^2\\)).
        - Do not include explanations, comments, or text outside the JSON array.
        """
    },
    {
        "role": "user",
        "content": f"Context/Topics for the quiz: {userTxt}"
    }
],
        extra_body={"reasoning": {"enabled": True}}
        )
        quiz_JSON = response.choices[0].message.content
        if shuffler_verify(quiz_JSON):
            return {"quiz_JSON": quiz_JSON, 'redflag': False}
        else:
            return {"quiz_JSON": quiz_JSON, 'redflag': True}

    except Exception as e:
        quiz_JSON = f"ERROR: {e}"
        flash("No API key found.", 'error')
        return {"quiz_JSON": quiz_JSON, 'redflag': True}



def shuffler(json_txt):
    import json
    import random
    txt_list = json.loads(json_txt)
    random.shuffle(txt_list)
    return txt_list









from openai import OpenAI

def notes_generator(api_key, mode, model='openai/gpt-oss-20b:free', lecture_doc=None):
    userTxt = ""
    
    # 1. Extraction with safety check
    if lecture_doc:
        print('Executing text extraction...')
        extracted = text_extractor(lecture_doc)
        # Ensure we are working with a string, not a function object or None
        userTxt = str(extracted) if extracted else ""

    if not userTxt.strip():
        return {"notes": "Error: No text could be extracted from the source document.", "redflag": True}

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # 2. Define Prompts (Deduplicated logic)
    if mode == 'briefDocs':
        system_content = (
            """Create a comprehensive briefing document that synthesizes the main themes and ideas from the sources. 
            Start with a concise Executive Summary that presents the most critical takeaways upfront. The body of the 
            document must provide a detailed and thorough examination of the main themes, evidence, and conclusions 
            found in the sources. This analysis should be structured logically with headings and bullet points to ensure 
            clarity. The tone must be objective and incisive."""
        )
    elif mode == 'studyGuide':
        system_content = (
            """You are a highly capable research assistant and tutor. Create a detailed study guide designed 
            to review understanding of the sources. Create a quiz with ten short-answer questions (2-3 sentences each) 
            and include a separate answer key. Suggest five essay format questions, but do not supply answers. 
            Also conclude with a comprehensive glossary of key terms with definitions."""
        )
    else:
        return {"notes": "Invalid mode selected.", "redflag": True}

    # 3. Single API Call Block
    try:
        print(f'Calling API for {mode}...')
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"Content from the source: {userTxt}"}
            ],
            extra_body={"reasoning": {"enabled": True}}
        )
        generated_notes = response.choices[0].message.content
        if not generated_notes or len(generated_notes) < 50:
            return {"notes": "AI failed to generate substantial content.", "redflag": True}

        return {"notes": generated_notes, 'redflag': False}

    except Exception as e:
        print(f"API Critical Failure: {e}")
        return {"notes": f"Generation Error: {str(e)}", "redflag": True}