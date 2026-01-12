import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class IntentPattern:
    """Pattern definition for intent matching"""
    keywords: List[str]
    patterns: List[str]
    entity_extractors: Dict[str, str]  # entity_name -> regex pattern
    priority: int = 1

class HRIntentRouter:
    """
    Routes HR service requests to appropriate intents based on NLP analysis
    """
    
    def __init__(self):
        self.intents = self._define_intents()
        self.month_map = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
    
    def _define_intents(self) -> Dict[str, IntentPattern]:
        """Define all HR intent patterns"""
        
        return {
            # ============ PAYROLL & PAYSLIP ============
            'payslip_download': IntentPattern(
                keywords=['payslip', 'pay slip', 'salary slip', 'wage slip', 'pay stub'],
                patterns=[
                    r'(need|want|get|download|send|share|provide)\s+.*payslip',
                    r'payslip\s+.*\s+(month|year|for)',
                    r'(december|january|february|march|april|may|june|july|august|september|october|november)\s+payslip',
                    r'payslip\s+(december|january|february|march|april|may|june|july|august|september|october|november)',
                    r'last\s+month.*payslip',
                    r'this\s+month.*payslip'
                ],
                entity_extractors={
                    'month': r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)',
                    'year': r'20\d{2}'
                },
                priority=1
            ),
            
            'pay_statement': IntentPattern(
                keywords=['pay statement', 'salary statement', 'ytd', 'year to date', 'earnings statement'],
                patterns=[
                    r'(need|want|get|download|send)\s+.*pay\s+statement',
                    r'salary\s+statement',
                    r'ytd\s+(salary|earnings|statement)',
                    r'year\s+to\s+date\s+(salary|statement)',
                    r'(from|between)\s+.*\s+(to|and)\s+.*statement'
                ],
                entity_extractors={
                    'from_month': r'from\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
                    'to_month': r'to\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
                    'year': r'20\d{2}'
                },
                priority=1
            ),
            
            'bank_account_change': IntentPattern(
                keywords=['bank account', 'salary account', 'account change', 'ifsc', 'bank change'],
                patterns=[
                    r'(change|update|modify)\s+.*bank\s+account',
                    r'(change|update|modify)\s+.*salary\s+account',
                    r'new\s+bank\s+account',
                    r'bank\s+account\s+change'
                ],
                entity_extractors={
                    'bank_name': r'(hdfc|icici|sbi|axis|kotak|yes bank|idfc|indusind)',
                    'account_number': r'\d{9,18}',
                    'ifsc': r'[A-Z]{4}0[A-Z0-9]{6}'
                },
                priority=2
            ),
            
            # ============ LEAVE & ATTENDANCE ============
            'apply_leave': IntentPattern(
                keywords=['leave', 'time off', 'day off', 'vacation', 'holiday'],
                patterns=[
                    r'(apply|request|need|want|take)\s+.*\s+leave',
                    r'leave\s+.*\s+(from|on|for)\s+',
                    r'(casual|sick|annual|earned|marriage|maternity|paternity)\s+leave',
                    r'off\s+on\s+\d',
                    r'leave\s+from\s+\d+\s+to\s+\d+'
                ],
                entity_extractors={
                    'leave_type': r'(casual|sick|medical|annual|earned|privilege|maternity|paternity|marriage|bereavement|comp)',
                    'from_date': r'from\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4}|\d{1,2}\s+\w+)',
                    'to_date': r'to\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4}|\d{1,2}\s+\w+)',
                    'single_date': r'on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4}|\d{1,2}\s+\w+)',
                    'reason': r'(for|because|due to)\s+(.+?)(?:\.|$)'
                },
                priority=1
            ),
            
            'attendance_correction': IntentPattern(
                keywords=['attendance', 'punch', 'swipe', 'clock in', 'clock out', 'time correction'],
                patterns=[
                    r'attendance\s+(correction|issue|problem|missing)',
                    r'(missed|forgot|forgotten)\s+(punch|swipe|clock)',
                    r'mark\s+.*\s+attendance',
                    r'attendance\s+not\s+(marked|recorded|showing)'
                ],
                entity_extractors={
                    'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})',
                    'time': r'(\d{1,2}:\d{2}\s*(am|pm)?)'
                },
                priority=2
            ),
            
            'leave_balance': IntentPattern(
                keywords=['leave balance', 'remaining leave', 'available leave', 'how many leaves'],
                patterns=[
                    r'(check|show|what is|how many)\s+.*\s+leave\s+balance',
                    r'leave\s+balance',
                    r'remaining\s+(leaves|leave)',
                    r'(available|pending)\s+leaves?'
                ],
                entity_extractors={
                    'leave_type': r'(casual|sick|annual|earned|privilege|all)'
                },
                priority=1
            ),
            
            # ============ LETTERS & CERTIFICATES ============
            'employment_letter': IntentPattern(
                keywords=['employment letter', 'experience letter', 'service letter', 'relieving letter'],
                patterns=[
                    r'(need|want|request|generate|issue)\s+.*employment\s+letter',
                    r'employment\s+(letter|certificate)',
                    r'(experience|service|relieving)\s+letter',
                    r'letter\s+(for|of)\s+employment'
                ],
                entity_extractors={
                    'letter_type': r'(employment|experience|service|relieving)',
                    'purpose': r'(for|purpose)\s+(.+?)(?:\.|$)'
                },
                priority=1
            ),
            
            'salary_certificate': IntentPattern(
                keywords=['salary certificate', 'income certificate', 'salary letter'],
                patterns=[
                    r'(need|want|request)\s+.*salary\s+certificate',
                    r'salary\s+(certificate|letter)',
                    r'income\s+(certificate|proof|letter)',
                    r'certificate\s+(for|of)\s+salary'
                ],
                entity_extractors={
                    'purpose': r'(for|purpose)\s+(.+?)(?:\.|$)'
                },
                priority=1
            ),
            
            'address_proof_letter': IntentPattern(
                keywords=['address proof', 'residence letter', 'bonafide certificate'],
                patterns=[
                    r'address\s+proof',
                    r'bonafide\s+(certificate|letter)',
                    r'residence\s+(proof|letter)'
                ],
                entity_extractors={
                    'purpose': r'(for|purpose)\s+(.+?)(?:\.|$)'
                },
                priority=2
            ),
            
            # ============ BENEFITS & INSURANCE ============
            'insurance_ecard': IntentPattern(
                keywords=['e-card', 'ecard', 'health card', 'insurance card', 'medi assist'],
                patterns=[
                    r'(need|want|request|download)\s+.*(e-?card|health\s+card|insurance\s+card)',
                    r'(medical|health)\s+insurance\s+card',
                    r'medi\s*assist\s+card',
                    r'group\s+insurance\s+(card|e-?card)'
                ],
                entity_extractors={
                    'for_whom': r'(self|spouse|child|parent|dependent|family)'
                },
                priority=1
            ),
            
            'add_dependent': IntentPattern(
                keywords=['add dependent', 'add family', 'dependent addition', 'newborn', 'new child'],
                patterns=[
                    r'add\s+.*\s+(dependent|family\s+member)',
                    r'(newborn|new\s+baby|new\s+child)\s+.*\s+(add|include|enroll)',
                    r'(include|enroll)\s+.*\s+(spouse|child|parent)',
                    r'dependent\s+(addition|enrollment)'
                ],
                entity_extractors={
                    'relationship': r'(spouse|child|son|daughter|parent|father|mother)',
                    'name': r'name\s*[:\-]?\s*([A-Za-z\s]+)'
                },
                priority=2
            ),
            
            'reimbursement_claim': IntentPattern(
                keywords=['reimbursement', 'claim', 'medical claim', 'expense claim'],
                patterns=[
                    r'(submit|raise|file)\s+.*\s+(reimbursement|claim)',
                    r'medical\s+(reimbursement|claim)',
                    r'(expense|travel)\s+claim',
                    r'claim\s+(reimbursement|expenses)'
                ],
                entity_extractors={
                    'claim_type': r'(medical|travel|expense|food)',
                    'amount': r'(?:rs\.?|inr|₹)\s*(\d+[,\d]*)'
                },
                priority=2
            ),
            
            # ============ EMPLOYEE DATA ============
            'update_contact': IntentPattern(
                keywords=['update phone', 'update email', 'update address', 'change contact', 'update mobile'],
                patterns=[
                    r'(update|change|modify)\s+.*(phone|mobile|email|address|contact)',
                    r'(new|changed)\s+(phone|mobile|email|address)',
                    r'contact\s+(update|change)'
                ],
                entity_extractors={
                    'field': r'(phone|mobile|email|address)',
                    'value': r'(?:to|is)\s+(.+?)(?:\.|$)'
                },
                priority=2
            ),
            
            'update_emergency_contact': IntentPattern(
                keywords=['emergency contact', 'emergency number'],
                patterns=[
                    r'(update|change|add)\s+.*\s+emergency\s+contact',
                    r'emergency\s+contact\s+(update|change)'
                ],
                entity_extractors={
                    'name': r'name\s*[:\-]?\s*([A-Za-z\s]+)',
                    'phone': r'(\d{10})'
                },
                priority=2
            ),

            'form16': IntentPattern(
                keywords=['form 16', 'form-16', 'tax certificate'],
                patterns=[
                    r'need\s+.*form\s*16',
                    r'form\s*16\s+for',
                    r'tax\s+certificate'
                ],
                entity_extractors={
                    'financial_year': r'20\d{2}-?\d{2}'
                },
                priority=1
            ),
            
            'policy_query': IntentPattern(
                keywords=['policy', 'rules', 'procedure', 'guidelines'],
                patterns=[
                    r'what\s+is\s+.*policy',
                    r'policy\s+on',
                    r'rules\s+for'
                ],
                entity_extractors={
                    'topic': r'(leave|attendance|benefits|insurance|travel|probation)'
                },
                priority=2
            )
        }

    def route(self, text: str) -> Dict[str, Any]:
        """
        Route the input text to a specific intent
        Returns dict with intent, confidence, and entities
        """
        text = text.lower().strip()
        best_intent = 'unknown'
        max_confidence = 0.0
        best_entities = {}

        # Check each intent
        for intent_name, strategy in self.intents.items():
            confidence = 0.0
            
            # 1. Keyword matching
            keyword_match_count = sum(1 for k in strategy.keywords if k in text)
            if keyword_match_count > 0:
                confidence += 0.3 + (0.1 * min(keyword_match_count, 3))
            
            # 2. Regex pattern matching
            for pattern in strategy.patterns:
                if re.search(pattern, text):
                    confidence += 0.4
                    break
            
            # 3. Entity presence boosts confidence
            entities = {}
            for entity_name, pattern in strategy.entity_extractors.items():
                match = re.search(pattern, text)
                if match:
                    # Clean up the match
                    val = match.group(1) if match.groups() else match.group(0)
                    entities[entity_name] = val.strip()
                    confidence += 0.1

            # Normalize confidence
            confidence = min(confidence, 1.0)
            
            # Priority boost
            if strategy.priority == 1 and confidence > 0.5:
                confidence += 0.1
                
            if confidence > max_confidence:
                max_confidence = confidence
                best_intent = intent_name
                best_entities = entities
        
        # Helper: Default entity inference (e.g. current month/year if missing)
        if best_intent == 'payslip_download':
            if 'month' not in best_entities:
                # If "last month" is mentioned, infer it
                if 'last month' in text:
                    last_month = datetime.now().replace(day=1) - timedelta(days=1)
                    best_entities['month'] = last_month.strftime('%B').lower()
                    best_entities['year'] = str(last_month.year)
                elif 'this month' in text:
                    best_entities['month'] = datetime.now().strftime('%B').lower()
                    best_entities['year'] = str(datetime.now().year)

        return {
            "intent": best_intent if max_confidence > 0.4 else "unknown",
            "confidence": min(max_confidence, 1.0),
            "entities": best_entities
        }

if __name__ == "__main__":
    # Test cases
    router = HRIntentRouter()
    test_inputs = [
        "I need my payslip for December 2024",
        "Please send me last month's salary slip", 
        "Apply casual leave from 15/01/2025 to 17/01/2025 for personal work",
        "Need employment letter for visa application",
        "Update my bank account to HDFC"
    ]
    
    print("="*60)
    print("HR Intent Router - Test Results")
    print("="*60 + "\n")
    
    for text in test_inputs:
        result = router.route(text)
        print(f"Input: {text}")
        print(f"Intent: {result['intent']}")
        print(f"Confidence: {result['confidence']:.0%}")
        print(f"Entities: {result['entities']}\n")
