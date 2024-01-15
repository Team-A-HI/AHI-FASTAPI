import unittest
import json
from resumegenerator import generate_resume, generate_resume_content

class ResumeGeneratorTest(unittest.TestCase):
    def setUp(self):
        with open('sample_resume_data.json', 'r', encoding='utf-8') as file:
            self.resume_data = json.load(file)

    def test_generate_resume(self):
        context = generate_resume(self.resume_data)
        self.assertIn('Name', context)  # 중괄호 없는 'Name'을 확인
        self.assertEqual('이름', context['Name'])  # '이름'이 Name 키의 값인지 확인

    def test_generate_resume_content(self):
        generated_path = generate_resume_content(self.resume_data)
        self.assertTrue(generated_path.endswith('.pdf'))

if __name__ == '__main__':
    unittest.main()