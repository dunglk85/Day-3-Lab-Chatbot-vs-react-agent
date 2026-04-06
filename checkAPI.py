import google.generativeai as genai

genai.configure(api_key="AIzaSyCi09PeYK_tmp6KMOhdzRfi_k74Wi1JK94")
model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content("What is 2+2?")
print(response.text)