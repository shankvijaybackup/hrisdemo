import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

# Simulated HRIS Database
HRIS_DB = {
    "employees": {},
    "leave_balances": {},
    "leave_requests": [],
    "attendance": {},
    "dependents": {}
}

class HRActionExecutor:
    """Executes HR actions based on intent"""
    
    def __init__(self, output_dir: str = "/tmp/hr_agent_outputs"):
        # Use a local temp dir since /tmp might not exist on Windows
        self.output_dir = os.path.join(os.getcwd(), "hr_outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize sample employee data
        self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize sample HRIS data"""
        HRIS_DB["employees"]["default"] = {
            "employee_id": "EMP001",
            "name": "John Doe",
            "email": "john.doe@drreddy.com",
            "department": "Research & Development",
            "designation": "Senior Scientist",
            "date_of_joining": "2020-03-15",
            "manager": "Dr. Sarah Smith",
            "location": "Hyderabad",
            "bank_account": {
                "bank_name": "HDFC Bank",
                "account_number": "XXXX5678",
                "ifsc": "HDFC0001234"
            },
            "salary": {
                "basic": 75000,
                "hra": 30000,
                "special_allowance": 25000,
                "pf_contribution": 9000,
                "professional_tax": 200,
                "income_tax": 15000,
                "gross": 130000,
                "net": 105800
            }
        }
        
        HRIS_DB["leave_balances"]["default"] = {
            "casual_leave": {"total": 12, "used": 3, "available": 9},
            "sick_leave": {"total": 12, "used": 2, "available": 10},
            "earned_leave": {"total": 15, "used": 5, "available": 10},
            "privilege_leave": {"total": 3, "used": 0, "available": 3}
        }
    
    async def execute(self, intent: str, entities: Dict, user_email: str, 
                      requester_name: str, ticket_id: str) -> Dict:
        """
        Execute the appropriate action based on intent
        """
        # Get or create employee profile
        employee = self._get_employee(user_email, requester_name)
        
        # Route to appropriate handler
        handlers = {
            'payslip_download': self._handle_payslip,
            'pay_statement': self._handle_pay_statement,
            'apply_leave': self._handle_leave_application,
            'leave_balance': self._handle_leave_balance,
            'employment_letter': self._handle_employment_letter,
            'salary_certificate': self._handle_salary_certificate,
            'insurance_ecard': self._handle_insurance_ecard,
            'attendance_correction': self._handle_attendance_correction,
            'bank_account_change': self._handle_bank_change,
            'add_dependent': self._handle_add_dependent,
            'form16': self._handle_form16,
            'update_contact': self._handle_contact_update,
            'policy_query': self._handle_policy_query,
            'unknown': self._handle_unknown
        }
        
        handler = handlers.get(intent, self._handle_unknown)
        return await handler(employee, entities, ticket_id)
    
    def _get_employee(self, email: str, name: str) -> Dict:
        """Get or create employee profile"""
        if email not in HRIS_DB["employees"]:
            # Create based on default with personalized info
            emp = HRIS_DB["employees"]["default"].copy()
            emp["email"] = email
            emp["name"] = name
            emp["employee_id"] = f"EMP{hash(email) % 10000:04d}"
            HRIS_DB["employees"][email] = emp
            HRIS_DB["leave_balances"][email] = HRIS_DB["leave_balances"]["default"].copy()
        return HRIS_DB["employees"].get(email, HRIS_DB["employees"]["default"])
    
    # ============ PAYSLIP HANDLERS ============
    
    async def _handle_payslip(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Generate payslip PDF"""
        month_str = entities.get('month', datetime.now().strftime('%B').lower())
        year_str = entities.get('year', str(datetime.now().year))
        
        # Parse month
        month_map = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'october': 10, 'oct': 10,
            'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        month_num = month_map.get(month_str.lower(), datetime.now().month)
        month_name = datetime(2024, month_num, 1).strftime('%B')
        
        # Generate payslip content
        salary = employee.get('salary', HRIS_DB["employees"]["default"]["salary"])
        
        payslip_data = {
            "employee_name": employee['name'],
            "employee_id": employee['employee_id'],
            "department": employee['department'],
            "designation": employee['designation'],
            "pay_period": f"{month_name} {year_str}",
            "earnings": {
                "Basic Salary": salary['basic'],
                "House Rent Allowance": salary['hra'],
                "Special Allowance": salary['special_allowance']
            },
            "deductions": {
                "Provident Fund": salary['pf_contribution'],
                "Professional Tax": salary['professional_tax'],
                "Income Tax (TDS)": salary['income_tax']
            },
            "gross_earnings": salary['gross'],
            "total_deductions": salary['pf_contribution'] + salary['professional_tax'] + salary['income_tax'],
            "net_pay": salary['net'],
            "bank_account": employee['bank_account']['account_number'],
            "bank_name": employee['bank_account']['bank_name']
        }
        
        # Generate PDF
        pdf_path = await self._generate_payslip_pdf(payslip_data, ticket_id)
        
        base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")
        download_url = f"{base_url}/downloads/payslip_{ticket_id}.pdf"
        
        return {
            "status": "success",
            "message": f"Payslip generated successfully for {month_name} {year_str}",
            "details": {
                "pay_period": f"{month_name} {year_str}",
                "gross_salary": f"₹{salary['gross']:,}",
                "net_salary": f"₹{salary['net']:,}",
                "credit_account": employee['bank_account']['account_number']
            },
            "attachment_path": pdf_path,
            "download_url": download_url
        }
    
    async def _handle_pay_statement(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Generate pay statement (YTD or date range)"""
        from_month = entities.get('from_month', 'april')
        to_month = entities.get('to_month', datetime.now().strftime('%B').lower())
        year = entities.get('year', str(datetime.now().year))
        
        salary = employee.get('salary', HRIS_DB["employees"]["default"]["salary"])
        
        # Calculate YTD totals (simplified)
        months_count = 9  # Apr to Dec
        ytd_gross = salary['gross'] * months_count
        ytd_deductions = (salary['pf_contribution'] + salary['professional_tax'] + salary['income_tax']) * months_count
        ytd_net = salary['net'] * months_count
        
        return {
        base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")
        download_url = f"{base_url}/downloads/pay_statement_{year}.pdf"

        return {
            "status": "success",
            "message": f"Pay statement generated for FY {year}",
            "details": {
                "period": f"April {year} to {to_month.title()} {year}",
                "ytd_gross_earnings": f"₹{ytd_gross:,}",
                "ytd_deductions": f"₹{ytd_deductions:,}",
                "ytd_net_pay": f"₹{ytd_net:,}",
                "months_covered": months_count
            },
            "download_url": download_url
        }
    
    async def _generate_payslip_pdf(self, data: Dict, ticket_id: str) -> str:
        """Generate a payslip PDF file"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            filename = os.path.join(self.output_dir, f"payslip_{ticket_id}.pdf")
            doc = SimpleDocTemplate(filename, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            
            # Title
            elements.append(Paragraph("<b>DR. REDDY'S LABORATORIES LIMITED</b>", styles['Title']))
            elements.append(Paragraph("PAYSLIP", styles['Heading2']))
            elements.append(Spacer(1, 20))
            
            # Employee Info
            info_data = [
                ["Employee Name:", data['employee_name'], "Employee ID:", data['employee_id']],
                ["Department:", data['department'], "Designation:", data['designation']],
                ["Pay Period:", data['pay_period'], "Bank A/C:", data['bank_account']]
            ]
            info_table = Table(info_data, colWidths=[100, 150, 100, 150])
            info_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 20))
            
            # Earnings & Deductions
            earnings_data = [["EARNINGS", "Amount (₹)", "DEDUCTIONS", "Amount (₹)"]]
            earnings_list = list(data['earnings'].items())
            deductions_list = list(data['deductions'].items())
            max_rows = max(len(earnings_list), len(deductions_list))
            
            for i in range(max_rows):
                row = []
                if i < len(earnings_list):
                    row.extend([earnings_list[i][0], f"{earnings_list[i][1]:,}"])
                else:
                    row.extend(["", ""])
                if i < len(deductions_list):
                    row.extend([deductions_list[i][0], f"{deductions_list[i][1]:,}"])
                else:
                    row.extend(["", ""])
                earnings_data.append(row)
            
            # Totals
            earnings_data.append(["Gross Earnings", f"{data['gross_earnings']:,}", 
                                 "Total Deductions", f"{data['total_deductions']:,}"])
            
            table = Table(earnings_data, colWidths=[150, 80, 150, 80])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3c6e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))
            
            # Net Pay
            net_data = [["NET PAY", f"₹ {data['net_pay']:,}"]]
            net_table = Table(net_data, colWidths=[380, 100])
            net_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            elements.append(net_table)
            
            elements.append(Spacer(1, 30))
            elements.append(Paragraph("<i>This is a system-generated payslip and does not require a signature.</i>", 
                                     styles['Normal']))
            
            doc.build(elements)
            logger.info(f"Generated payslip PDF: {filename}")
            return filename
            
        except ImportError:
            # Fallback if reportlab not available
            logger.warning("reportlab not available, creating text-based payslip")
            filename = os.path.join(self.output_dir, f"payslip_{ticket_id}.txt")
            with open(filename, 'w') as f:
                f.write("=" * 60 + "\n")
                f.write("           DR. REDDY'S LABORATORIES LIMITED\n")
                f.write("                      PAYSLIP\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Employee: {data['employee_name']} ({data['employee_id']})\n")
                f.write(f"Period: {data['pay_period']}\n\n")
                f.write("EARNINGS:\n")
                for name, amount in data['earnings'].items():
                    f.write(f"  {name}: ₹{amount:,}\n")
                f.write(f"\nGross: ₹{data['gross_earnings']:,}\n")
                f.write("\nDEDUCTIONS:\n")
                for name, amount in data['deductions'].items():
                    f.write(f"  {name}: ₹{amount:,}\n")
                f.write(f"\nTotal Deductions: ₹{data['total_deductions']:,}\n")
                f.write(f"\n{'='*60}\n")
                f.write(f"NET PAY: ₹{data['net_pay']:,}\n")
                f.write(f"{'='*60}\n")
            return filename
    
    # ============ LEAVE HANDLERS ============
    
    async def _handle_leave_application(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Process leave application"""
        leave_type = entities.get('leave_type', 'casual_leave')
        from_date = entities.get('from_date', entities.get('single_date', 'Not specified'))
        to_date = entities.get('to_date', from_date)
        reason = entities.get('reason', 'Personal work')
        
        # Get leave balance
        email = employee['email']
        balances = HRIS_DB["leave_balances"].get(email, HRIS_DB["leave_balances"]["default"])
        
        leave_type_key = leave_type.lower().replace(' ', '_')
        if leave_type_key not in balances:
            leave_type_key = 'casual_leave'
        
        available = balances[leave_type_key]['available']
        
        # Calculate days (simplified)
        try:
            days = 1
            if from_date != to_date:
                # Try to parse and calculate
                days = 3  # Default for multi-day
        except:
            days = 1
        
        if available < days:
            return {
                "status": "warning",
                "message": f"Insufficient leave balance. You have {available} {leave_type.replace('_', ' ')} days available.",
                "details": {
                    "leave_type": leave_type.replace('_', ' ').title(),
                    "requested_days": days,
                    "available_balance": available,
                    "action_required": "Please select a different leave type or reduce the number of days"
                }
            }
        
        # Create leave request
        leave_request = {
            "id": f"LR-{ticket_id}",
            "employee_id": employee['employee_id'],
            "employee_name": employee['name'],
            "leave_type": leave_type,
            "from_date": from_date,
            "to_date": to_date,
            "days": days,
            "reason": reason,
            "status": "Pending Approval",
            "applied_on": datetime.now().isoformat(),
            "manager": employee.get('manager', 'Manager')
        }
        HRIS_DB["leave_requests"].append(leave_request)
        
        # Update balance (tentatively)
        balances[leave_type_key]['available'] -= days
        balances[leave_type_key]['used'] += days
        
        return {
            "status": "success",
            "message": f"Leave application submitted successfully. Pending approval from {employee.get('manager', 'your manager')}.",
            "details": {
                "leave_request_id": leave_request['id'],
                "leave_type": leave_type.replace('_', ' ').title(),
                "from_date": from_date,
                "to_date": to_date,
                "days": days,
                "reason": reason,
                "status": "Pending Approval",
                "remaining_balance": balances[leave_type_key]['available'],
                "calendar_event": f"Out of Office: {from_date} to {to_date}"
            }
        }
    
    async def _handle_leave_balance(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Return leave balance"""
        email = employee['email']
        balances = HRIS_DB["leave_balances"].get(email, HRIS_DB["leave_balances"]["default"])
        
        leave_type = entities.get('leave_type', 'all')
        
        if leave_type and leave_type != 'all':
            leave_type_key = leave_type.lower().replace(' ', '_')
            if leave_type_key in balances:
                bal = balances[leave_type_key]
                return {
                    "status": "success",
                    "message": f"Your {leave_type.replace('_', ' ').title()} balance: {bal['available']} days available",
                    "details": {
                        "leave_type": leave_type.replace('_', ' ').title(),
                        "total_entitled": bal['total'],
                        "used": bal['used'],
                        "available": bal['available']
                    }
                }
        
        # Return all balances
        balance_details = {}
        total_available = 0
        for lt, bal in balances.items():
            balance_details[lt.replace('_', ' ').title()] = f"{bal['available']} of {bal['total']} days"
            total_available += bal['available']
        
        return {
            "status": "success",
            "message": f"Total available leave: {total_available} days across all categories",
            "details": balance_details
        }
    
    # ============ LETTER HANDLERS ============
    
    async def _handle_employment_letter(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Generate employment verification letter"""
        purpose = entities.get('purpose', 'general verification')
        letter_type = entities.get('letter_type', 'employment')
        
        letter_data = {
            "employee_name": employee['name'],
            "employee_id": employee['employee_id'],
            "designation": employee['designation'],
            "department": employee['department'],
            "date_of_joining": employee['date_of_joining'],
            "purpose": purpose,
            "letter_type": letter_type,
            "company": "Dr. Reddy's Laboratories Limited",
            "date": datetime.now().strftime("%d %B %Y")
        }
        
        pdf_path = await self._generate_letter_pdf(letter_data, ticket_id)
        
        return {
        base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")
        download_url = f"{base_url}/downloads/{letter_type}_letter_{ticket_id}.pdf"
        
        return {
            "status": "success",
            "message": f"{letter_type.title()} letter generated successfully",
            "details": {
                "letter_type": letter_type.title(),
                "employee_name": employee['name'],
                "designation": employee['designation'],
                "date_of_joining": employee['date_of_joining'],
                "purpose": purpose,
                "generated_on": letter_data['date']
            },
            "attachment_path": pdf_path,
            "download_url": download_url
        }
    
    async def _generate_letter_pdf(self, data: Dict, ticket_id: str) -> str:
        """Generate employment letter PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            filename = os.path.join(self.output_dir, f"{data['letter_type']}_letter_{ticket_id}.pdf")
            doc = SimpleDocTemplate(filename, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            
            # Header
            elements.append(Paragraph("<b>DR. REDDY'S LABORATORIES LIMITED</b>", styles['Title']))
            elements.append(Paragraph("8-2-337, Road No. 3, Banjara Hills, Hyderabad - 500034", styles['Normal']))
            elements.append(Spacer(1, 30))
            
            # Date
            elements.append(Paragraph(f"Date: {data['date']}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Subject
            elements.append(Paragraph(f"<b>TO WHOM IT MAY CONCERN</b>", styles['Heading2']))
            elements.append(Spacer(1, 20))
            
            # Body
            body_text = f"""
            This is to certify that <b>{data['employee_name']}</b> (Employee ID: {data['employee_id']}) 
            is employed with Dr. Reddy's Laboratories Limited as <b>{data['designation']}</b> in the 
            <b>{data['department']}</b> department since <b>{data['date_of_joining']}</b>.
            <br/><br/>
            As of the date of this letter, {data['employee_name']} continues to be a full-time employee 
            of our organization.
            <br/><br/>
            This letter is being issued at the request of the employee for the purpose of <b>{data['purpose']}</b>.
            <br/><br/>
            We wish {data['employee_name']} all the best in their endeavors.
            """
            elements.append(Paragraph(body_text, styles['Normal']))
            elements.append(Spacer(1, 40))
            
            # Signature
            elements.append(Paragraph("<b>For Dr. Reddy's Laboratories Limited</b>", styles['Normal']))
            elements.append(Spacer(1, 30))
            elements.append(Paragraph("_______________________", styles['Normal']))
            elements.append(Paragraph("Authorized Signatory", styles['Normal']))
            elements.append(Paragraph("Human Resources Department", styles['Normal']))
            
            doc.build(elements)
            return filename
            
        except ImportError:
            filename = os.path.join(self.output_dir, f"{data['letter_type']}_letter_{ticket_id}.txt")
            with open(filename, 'w') as f:
                f.write("DR. REDDY'S LABORATORIES LIMITED\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Date: {data['date']}\n\n")
                f.write("TO WHOM IT MAY CONCERN\n\n")
                f.write(f"This is to certify that {data['employee_name']} (ID: {data['employee_id']})\n")
                f.write(f"is employed as {data['designation']} in {data['department']}\n")
                f.write(f"since {data['date_of_joining']}.\n\n")
                f.write("For Dr. Reddy's Laboratories Limited\n")
                f.write("Human Resources Department\n")
            return filename
    
    async def _handle_salary_certificate(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Generate salary certificate"""
        salary = employee.get('salary', HRIS_DB["employees"]["default"]["salary"])
        purpose = entities.get('purpose', 'general verification')
        
        return {
        base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")
        download_url = f"{base_url}/downloads/salary_certificate.pdf"
        
        return {
            "status": "success",
            "message": "Salary certificate generated successfully",
            "details": {
                "employee_name": employee['name'],
                "designation": employee['designation'],
                "annual_ctc": f"₹{salary['gross'] * 12:,}",
                "monthly_gross": f"₹{salary['gross']:,}",
                "purpose": purpose,
                "generated_on": datetime.now().strftime("%d %B %Y")
            },
            "download_url": download_url
        }
    
    # ============ BENEFITS HANDLERS ============
    
    async def _handle_insurance_ecard(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Generate insurance e-card"""
        for_whom = entities.get('for_whom', 'self')
        
        ecard_data = {
            "policy_number": f"GMC-{employee['employee_id']}-2024",
            "employee_name": employee['name'],
            "employee_id": employee['employee_id'],
            "insurer": "ICICI Lombard",
            "tpa": "Medi Assist",
            "sum_insured": "₹5,00,000",
            "valid_from": "01-Apr-2024",
            "valid_to": "31-Mar-2025",
            "for_member": for_whom.title()
        }
        
        return {
        base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")
        download_url = f"{base_url}/downloads/insurance_ecard.pdf"
        
        return {
            "status": "success",
            "message": f"Insurance e-card generated for {for_whom}",
            "details": ecard_data,
            "download_url": download_url
        }
    
    async def _handle_add_dependent(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Process dependent addition request"""
        relationship = entities.get('relationship', 'dependent')
        name = entities.get('name', 'Not specified')
        
        return {
            "status": "pending",
            "message": "Dependent addition request submitted. HR team will verify and process within 3-5 business days.",
            "details": {
                "request_id": f"DEP-{ticket_id}",
                "dependent_name": name,
                "relationship": relationship.title(),
                "status": "Pending Verification",
                "documents_required": "Please submit: Birth Certificate/Marriage Certificate, Aadhaar Card, Photo",
                "expected_completion": (datetime.now() + timedelta(days=5)).strftime("%d %B %Y")
            }
        }
    
    # ============ OTHER HANDLERS ============
    
    async def _handle_attendance_correction(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Process attendance correction request"""
        date = entities.get('date', 'Not specified')
        time = entities.get('time', 'Not specified')
        
        return {
            "status": "pending",
            "message": "Attendance correction request submitted. Awaiting manager approval.",
            "details": {
                "request_id": f"ATT-{ticket_id}",
                "date": date,
                "time": time,
                "status": "Pending Manager Approval",
                "manager": employee.get('manager', 'Manager')
            }
        }
    
    async def _handle_bank_change(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Process bank account change request"""
        bank_name = entities.get('bank_name', 'New Bank')
        
        return {
            "status": "pending",
            "message": "Bank account change request submitted. Please upload cancelled cheque for verification.",
            "details": {
                "request_id": f"BNK-{ticket_id}",
                "new_bank": bank_name.upper() if bank_name else "Not specified",
                "status": "Awaiting Document Upload",
                "documents_required": "Cancelled cheque, Passbook front page",
                "effective_from": "Next payroll cycle"
            }
        }
    
    async def _handle_form16(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Generate Form 16"""
        fy = entities.get('financial_year', '2023-24')
        
        return {
        base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")
        download_url = f"{base_url}/downloads/form16_{fy}.pdf"
        
        return {
            "status": "success",
            "message": f"Form 16 for FY {fy} is available for download",
            "details": {
                "financial_year": fy,
                "employee_name": employee['name'],
                "pan": "XXXXX1234X",
                "total_income": "₹15,60,000",
                "tax_paid": "₹1,80,000"
            },
            "download_url": download_url
        }
    
    async def _handle_contact_update(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Process contact update request"""
        field = entities.get('field', 'contact')
        value = entities.get('value', 'Not specified')
        
        return {
            "status": "success",
            "message": f"{field.title()} update request processed successfully",
            "details": {
                "field_updated": field.title(),
                "new_value": value,
                "status": "Updated",
                "updated_on": datetime.now().strftime("%d %B %Y %H:%M")
            }
        }
    
    async def _handle_policy_query(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Handle policy/procedure queries"""
        topic = entities.get('topic', 'general')
        
        policy_info = {
            "leave": "Leave policy: Casual Leave - 12 days, Sick Leave - 12 days, Earned Leave - 15 days. Apply via HRIS portal.",
            "attendance": "Attendance policy: Core hours 10 AM - 5 PM. Flexi timing available. Regularization within 3 days.",
            "benefits": "Benefits: Group Medical Insurance (₹5L), Group Term Life, Gratuity, PF. Contact HR for details.",
            "insurance": "Health Insurance: ICICI Lombard via Medi Assist TPA. E-card available on HRIS. Cashless at network hospitals.",
            "travel": "Travel policy: Book via Concur. Domestic - 7 days advance. International - 21 days advance."
        }
        
        info = policy_info.get(topic.lower(), "Please contact HR for detailed policy information.")
        
        return {
            "status": "info",
            "message": info,
            "details": {
                "topic": topic.title(),
                "for_detailed_info": "Contact HR at hr.helpdesk@drreddy.com"
            }
        }
    
    async def _handle_unknown(self, employee: Dict, entities: Dict, ticket_id: str) -> Dict:
        """Handle unknown intents"""
        return {
            "status": "needs_clarification",
            "message": "I couldn't understand the specific HR request. This ticket has been flagged for manual review.",
            "details": {
                "action_required": "HR team will review and respond",
                "common_requests": [
                    "Payslip download",
                    "Leave application",
                    "Employment letter",
                    "Insurance e-card",
                    "Leave balance check"
                ]
            }
        }
