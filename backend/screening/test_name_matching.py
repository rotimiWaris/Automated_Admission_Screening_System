from django.test import SimpleTestCase
from .identities import names_match, candidate_name_issues
from .test_specimen_format import EXAM
from io import BytesIO
from openpyxl import Workbook
from .applicant_data import HEADERS
from .table_import import import_students

class NameMatchingTests(SimpleTestCase):
    def test_formatting_and_order(self):
        for a,b in [('Ade John James','JAMES ADE JOHN'),('Ade Abdul Wahad','ABDULWAHAD ADE'),('Anne-Marie Test','Test Anne Marie'),('Ade Adebayo','ADEBAYO ADE')]:
            with self.subTest(a=a):self.assertTrue(names_match(a,b))

    def test_real_spelling_missing_and_extra_names_still_fail(self):
        for a,b in [('Test Isreal','Test Israel'),('Ade John','Ade Johnson'),('Ade John James','Ade John'),('Test Timileyin','Test Tim Ilehin'),('',''),('Jane','Jean')]:
            with self.subTest(a=a):self.assertFalse(names_match(a,b))

    def test_jamb_match_is_sufficient(self):
        self.assertEqual(candidate_name_issues('Different Name','Candidate Name:TEST EXAMPLE',jamb_name='Example Test'),[])
        self.assertEqual(candidate_name_issues('Example Test','Candidate Name:TEST EXAMPLE',jamb_name='Other Name'),[])
        issues=candidate_name_issues('Other Name','Candidate Name:TEST EXAMPLE',jamb_name='Another Name')
        self.assertEqual(len(issues),1)
        self.assertIn('Name on JAMB',issues[0])
        self.assertEqual(len(candidate_name_issues('Example Test', 'Candidate Name:EXAMPLE TEST\nCandidate Name:EXAMPLE OTHER', jamb_name='Example Test')),1)

    def test_import_passes_jamb_name_to_comparison(self):
        values=dict.fromkeys(HEADERS,'')
        values.update({'Surname':'Different','First Name':'Name','Name on Jamb':'Fictional Applicant','Form No.':'FORM-TEST','Jamb reg':'JAMB-TEST','jamb programme':'Marketing','jamb score':'200','jamb subject':'English Language;Mathematics;Economics;Commerce','sitting(s)':'1','olevel result sitting 1':EXAM})
        w=Workbook();w.active.append(HEADERS);w.active.append([values[h] for h in HEADERS]);stream=BytesIO();w.save(stream)
        draft=import_students(stream.getvalue(),'names.xlsx')[0][0]
        self.assertFalse(any('does not match' in issue for issue in draft['review_issues']))

    def test_smart_processing_is_opt_in_and_retains_notice(self):
        text='Candidate Name:TEST ISRAEL'
        self.assertEqual(len(candidate_name_issues('Test Isreal',text)),1)
        warnings=[]
        self.assertEqual(candidate_name_issues('Test Isreal',text,smart_processing=True,warnings=warnings),[])
        self.assertIn('Original names were retained',warnings[0])
        self.assertIn('ISRAEL',warnings[0])
        self.assertIn('Isreal',warnings[0])

    def test_smart_processing_does_not_accept_missing_or_larger_differences(self):
        from .identities import minor_name_typo
        for a,b in [('Test Isreal','Test Israel'),('Test Israell','Test Israel'),('Test Israil','Test Israel')]:
            self.assertTrue(minor_name_typo(a,b))
        for a,b in [('Test Israel James','Test Israel'),('Test John','Test Johnson'),('Israel','Isreal'),('Test Jon','Test Jan'),('Tast Isreal','Test Israel')]:
            self.assertFalse(minor_name_typo(a,b))
            self.assertTrue(candidate_name_issues(a,'Candidate Name:'+b,smart_processing=True,warnings=[]))

    def test_long_excel_notes_keep_all_text_and_grow(self):
        from .screening_export import sized_comment
        from zipfile import ZipFile
        short=sized_comment(['Decision: Qualified'])
        long=sized_comment(['Decision: Pending Review','Detailed reason '*250+'FINAL_MARKER'])
        self.assertGreater(long.height,short.height)
        book=Workbook();book.active['A1'].comment=long
        stream=BytesIO();book.save(stream)
        with ZipFile(stream) as archive:
            comments=archive.read('xl/comments/comment1.xml').decode()
            self.assertIn('FINAL_MARKER',comments)
            drawing=archive.read('xl/drawings/commentsDrawing1.vml').decode()
            self.assertIn('height:'+str(long.height)+'px',drawing)
