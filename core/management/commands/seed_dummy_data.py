from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core import models
from core.crud import MODEL_REGISTRY


class Command(BaseCommand):
    help = "Create at least five dummy records for each ERP module."

    def handle(self, *args, **options):
        today = timezone.localdate()

        roles = self.create_roles()
        positions = self.create_positions()
        clients = self.create_clients(today)
        sites = self.create_sites(clients)
        self.create_contracts(clients, sites, today)
        shifts = self.create_shifts()
        employees = self.create_employees(roles, positions, today)
        guards = self.create_guards(employees[:5])
        supervisors = self.create_supervisors(employees[5:10])
        zones = self.create_zones(supervisors)
        deployments = self.create_deployments(guards, clients, sites, shifts, supervisors, today)
        schedules = self.create_schedules(deployments, today)

        self.create_zone_guard_allocations(zones, guards, today)
        self.create_zone_site_allocations(zones, sites, today)
        self.create_incidents(deployments, employees, today)
        self.create_patrol_logs(guards, sites, today)
        self.create_assets(employees, today)
        self.create_trainings(employees, today)
        self.create_recruitment(positions, employees, today)
        self.create_attendance(schedules, employees, shifts, today)
        self.create_leaves(employees, today)
        self.create_disciplinary_actions(employees, today)
        self.create_performance_evaluations(employees, today)
        self.create_documents(employees, today)
        self.create_salaries(employees, today)
        self.create_advances(employees, today)
        invoices = self.create_invoices(clients, today)
        self.create_payments(invoices, employees, today)
        self.create_budgets()
        self.create_expenses(employees, today)

        counts = [(config.title, config.model.objects.count()) for config in MODEL_REGISTRY.values()]
        for title, count in counts:
            self.stdout.write(f"{title}: {count}")
        self.stdout.write(self.style.SUCCESS("Dummy data seed complete."))

    def create_roles(self):
        data = [
            ("Demo Guard", models.DepartmentChoices.OPERATIONS),
            ("Demo Supervisor", models.DepartmentChoices.OPERATIONS),
            ("Demo HR Officer", models.DepartmentChoices.HUMAN_RESOURCE),
            ("Demo Accountant", models.DepartmentChoices.FINANCE),
            ("Demo Operations Manager", models.DepartmentChoices.ADMIN),
        ]
        return [
            models.Role.objects.get_or_create(
                role_name=name,
                defaults={"department": department, "description": "Demo role for sample data."},
            )[0]
            for name, department in data
        ]

    def create_positions(self):
        data = [
            ("Demo Security Guard", models.DepartmentChoices.OPERATIONS, "G1", "350000.00", "650000.00"),
            ("Demo Field Supervisor", models.DepartmentChoices.OPERATIONS, "S1", "700000.00", "1100000.00"),
            ("Demo HR Coordinator", models.DepartmentChoices.HUMAN_RESOURCE, "H1", "800000.00", "1300000.00"),
            ("Demo Finance Assistant", models.DepartmentChoices.FINANCE, "F1", "750000.00", "1250000.00"),
            ("Demo Branch Manager", models.DepartmentChoices.ADMIN, "M1", "1500000.00", "2500000.00"),
        ]
        return [
            models.Position.objects.get_or_create(
                position_title=title,
                defaults={
                    "department": department,
                    "grade_level": grade,
                    "salary_range_min": Decimal(minimum),
                    "salary_range_max": Decimal(maximum),
                    "description": "Demo position for sample data.",
                },
            )[0]
            for title, department, grade, minimum, maximum in data
        ]

    def create_clients(self, today):
        clients = []
        for index in range(1, 6):
            client, _created = models.Client.objects.update_or_create(
                client_name=f"Demo Client {index}",
                defaults={
                    "contact_person": f"Contact Person {index}",
                    "phone_number": f"07010000{index}",
                    "email": f"client{index}@demo.test",
                    "address": f"Demo business address {index}, Kampala",
                    "contract_start_date": today - timedelta(days=120 + index),
                    "contract_end_date": today + timedelta(days=365),
                    "contract_status": models.StatusChoices.ACTIVE,
                },
            )
            clients.append(client)
        return clients

    def create_sites(self, clients):
        sites = []
        for index, client in enumerate(clients, start=1):
            site, _created = models.Site.objects.update_or_create(
                client=client,
                site_name=f"Demo Site {index}",
                defaults={
                    "site_address": f"Plot {index}, Demo Road",
                    "city": "Kampala",
                    "state": "Central",
                    "security_level": ["Low", "Medium", "High", "Critical", "Medium"][index - 1],
                    "required_guards_per_shift": 5,
                    "notes": "Demo site for sample data.",
                },
            )
            sites.append(site)
        return sites

    def create_contracts(self, clients, sites, today):
        for index, client in enumerate(clients, start=1):
            contract, _created = models.Contract.objects.update_or_create(
                contract_number=f"DEMO-CON-{index:04d}",
                defaults={
                    "client": client,
                    "service_type": "Manned Guarding",
                    "start_date": today - timedelta(days=120 + index),
                    "end_date": today + timedelta(days=365),
                    "billing_rate": Decimal("1500000.00") + Decimal(index * 100000),
                    "status": models.StatusChoices.ACTIVE,
                    "terms": "Demo contract for sample data.",
                },
            )
            models.ContractSiteRequirement.objects.update_or_create(
                contract=contract,
                site=sites[index - 1],
                shift=None,
                start_date=contract.start_date,
                defaults={
                    "required_guards": 5,
                    "end_date": contract.end_date,
                    "status": models.StatusChoices.ACTIVE,
                    "notes": "Demo site requirement.",
                },
            )

    def create_shifts(self):
        data = [
            ("Morning", "M", time(6, 0), time(14, 0)),
            ("Day", "D", time(8, 0), time(20, 0)),
            ("Evening", "E", time(14, 0), time(22, 0)),
            ("Night", "N", time(18, 0), time(6, 0)),
            ("Weekend", "W", time(9, 0), time(17, 0)),
        ]
        return [
            models.Shift.objects.update_or_create(
                code=code,
                defaults={
                    "shift_name": name,
                    "start_time": start,
                    "end_time": end,
                    "description": "Demo shift for sample data.",
                },
            )[0]
            for name, code, start, end in data
        ]

    def create_employees(self, roles, positions, today):
        employees = []
        for index in range(1, 11):
            role = roles[0] if index <= 5 else roles[1]
            position = positions[0] if index <= 5 else positions[1]
            employee, _created = models.Employee.objects.update_or_create(
                email=f"employee{index}@demo.test",
                defaults={
                    "first_name": f"Demo{index}",
                    "last_name": "Employee",
                    "date_of_birth": date(1990, min(index, 12), min(index, 28)),
                    "gender": "Female" if index % 2 else "Male",
                    "phone_number": f"07120000{index:02d}",
                    "address": f"Demo employee address {index}",
                    "national_id": f"DEMO-NIN-{index:04d}",
                    "role": role,
                    "position": position,
                    "hire_date": today - timedelta(days=30 * index),
                    "status": models.StatusChoices.ACTIVE,
                },
            )
            employees.append(employee)
        return employees

    def create_guards(self, employees):
        guards = []
        for index, employee in enumerate(employees, start=1):
            employee.uniform_size = ["S", "M", "L", "XL", "XXL"][index - 1]
            employee.qualification = "Basic security certification"
            employee.armed_status = index % 2 == 0
            employee.training_level = ["Basic", "Intermediate", "Advanced", "Basic", "Advanced"][index - 1]
            employee.company_number = f"DEMO-G-{index:03d}"
            employee.license_no = f"DEMO-LIC-{index:03d}"
            employee.save(
                update_fields=[
                    "uniform_size",
                    "qualification",
                    "armed_status",
                    "training_level",
                    "company_number",
                    "license_no",
                    "updated_at",
                ]
            )
            guards.append(employee)
        return guards

    def create_supervisors(self, employees):
        supervisors = []
        for index, employee in enumerate(employees, start=1):
            employee.assigned_zone = f"Demo Zone {index}"
            employee.experience_years = index + 1
            employee.authority_level = ["Team Lead", "Area Lead", "Senior Lead", "Coordinator", "Controller"][index - 1]
            employee.save(update_fields=["assigned_zone", "experience_years", "authority_level", "updated_at"])
            supervisors.append(employee)
        return supervisors

    def create_zones(self, supervisors):
        zones = []
        for index, supervisor in enumerate(supervisors, start=1):
            zone, _created = models.Zone.objects.update_or_create(
                zone_code=f"DEMO-ZN-{index:03d}",
                defaults={
                    "zone_name": f"Demo Zone {index}",
                    "supervisor": supervisor,
                    "description": "Demo zone for sample data.",
                    "status": models.StatusChoices.ACTIVE,
                },
            )
            zones.append(zone)
        return zones

    def create_deployments(self, guards, clients, sites, shifts, supervisors, today):
        deployments = []
        for index in range(5):
            deployment, _created = models.Deployment.objects.update_or_create(
                employee=guards[index],
                site=sites[index],
                start_date=today - timedelta(days=10 + index),
                defaults={
                    "client": clients[index],
                    "supervisor": supervisors[index],
                    "shift": shifts[index],
                    "end_date": None,
                    "status": models.StatusChoices.ACTIVE,
                },
            )
            deployments.append(deployment)
        return deployments

    def create_schedules(self, deployments, today):
        schedules = []
        for index, deployment in enumerate(deployments):
            schedule, _created = models.GuardSchedule.objects.update_or_create(
                deployment=deployment,
                shift_date=today + timedelta(days=index),
                defaults={
                    "employee": deployment.employee,
                    "site": deployment.site,
                    "shift": deployment.shift,
                    "status": models.GuardSchedule.ScheduleStatus.SCHEDULED,
                    "notes": "Demo schedule.",
                },
            )
            schedules.append(schedule)
        return schedules

    def create_zone_guard_allocations(self, zones, guards, today):
        for index, guard in enumerate(guards):
            models.ZoneEmployeeAllocation.objects.update_or_create(
                employee=guard,
                status=models.StatusChoices.ACTIVE,
                end_date=None,
                defaults={"zone": zones[index], "start_date": today - timedelta(days=20), "notes": "Demo allocation."},
            )

    def create_zone_site_allocations(self, zones, sites, today):
        for index, site in enumerate(sites):
            models.ZoneSiteAllocation.objects.update_or_create(
                site=site,
                status=models.StatusChoices.ACTIVE,
                end_date=None,
                defaults={"zone": zones[index], "start_date": today - timedelta(days=20), "notes": "Demo allocation."},
            )

    def create_incidents(self, deployments, employees, today):
        incident_types = ["Access Control", "Perimeter Check", "Lost Item", "Noise Complaint", "Safety Hazard"]
        for index, deployment in enumerate(deployments, start=1):
            models.Incident.objects.update_or_create(
                deployment=deployment,
                incident_type=f"Demo {incident_types[index - 1]}",
                incident_date=timezone.make_aware(datetime.combine(today - timedelta(days=index), time(9 + index, 15))),
                defaults={
                    "employee": deployment.employee,
                    "description": "Demo incident description for testing.",
                    "location": f"Demo location {index}",
                    "severity_level": ["Low", "Medium", "Low", "High", "Medium"][index - 1],
                    "reported_by": employees[index - 1],
                    "status": models.StatusChoices.PENDING,
                },
            )

    def create_patrol_logs(self, guards, sites, today):
        for index, guard in enumerate(guards, start=1):
            models.PatrolLog.objects.update_or_create(
                employee=guard,
                patrol_time=timezone.make_aware(datetime.combine(today - timedelta(days=index), time(20, index))),
                defaults={
                    "site": sites[index - 1],
                    "patrol_route": f"Demo Route {index}",
                    "observations": "Demo patrol observation.",
                },
            )

    def create_assets(self, employees, today):
        for index in range(1, 6):
            models.Asset.objects.update_or_create(
                serial_number=f"DEMO-ASSET-{index:04d}",
                defaults={
                    "asset_name": ["Radio", "Torch", "Baton", "Reflector Jacket", "Metal Detector"][index - 1],
                    "asset_type": ["Communication", "Lighting", "Safety", "Uniform", "Screening"][index - 1],
                    "quantity": index,
                    "condition": ["Good", "Good", "Fair", "New", "Good"][index - 1],
                    "assigned_to": employees[index - 1],
                    "issue_date": today - timedelta(days=index),
                },
            )

    def create_trainings(self, employees, today):
        for index, employee in enumerate(employees[:5], start=1):
            models.Training.objects.update_or_create(
                employee=employee,
                training_name=f"Demo Training {index}",
                defaults={
                    "course_code": f"SEC-{index:03d}",
                    "training_type": [
                        models.Training.TrainingType.INDUCTION,
                        models.Training.TrainingType.FIRE_SAFETY,
                        models.Training.TrainingType.FIRST_AID,
                        models.Training.TrainingType.RADIO_COMMUNICATION,
                        models.Training.TrainingType.SITE_PROCEDURES,
                    ][index - 1],
                    "training_objective": "Build job-ready competence and document compliance for deployment.",
                    "provider": "Demo Security Academy",
                    "trainer_name": ["John Trainer", "Sarah Instructor", "Grace Medic", "Peter Control", "Moses Supervisor"][index - 1],
                    "trainer_contact": f"07000009{index:02d}",
                    "venue": ["Head Office", "Client Site", "Training Room A", "Control Room", "Main Gate"][index - 1],
                    "start_date": today - timedelta(days=40 + index),
                    "end_date": today - timedelta(days=35 + index),
                    "duration_hours": 16 + index,
                    "budgeted_cost": Decimal("180000.00") + Decimal(index * 25000),
                    "training_cost": Decimal("150000.00") + Decimal(index * 25000),
                    "pass_mark": 70,
                    "score": Decimal("75.00") + Decimal(index),
                    "result": models.Training.TrainingResult.PASSED,
                    "certificate_no": f"DEMO-CERT-{index:04d}",
                    "expiry_date": today + timedelta(days=365 - index),
                    "next_refresh_date": today + timedelta(days=335 - index),
                    "status": models.StatusChoices.APPROVED,
                    "action_notes": "Certified and ready for deployment.",
                },
            )

    def create_recruitment(self, positions, employees, today):
        requisitions = []
        for index in range(1, 4):
            requisition, _created = models.RecruitmentRequisition.objects.update_or_create(
                requisition_number=f"REQ-{today:%Y}-{index:03d}",
                defaults={
                    "vacancy_title": ["Security Guard", "Field Supervisor", "Control Room Operator"][index - 1],
                    "position": positions[min(index - 1, len(positions) - 1)],
                    "department": models.DepartmentChoices.OPERATIONS,
                    "requested_by": employees[5],
                    "number_of_openings": [10, 2, 3][index - 1],
                    "employment_type": models.RecruitmentRequisition.EmploymentType.FULL_TIME,
                    "work_location": ["Kampala", "Entebbe", "Head Office"][index - 1],
                    "opening_date": today - timedelta(days=20 + index),
                    "closing_date": today + timedelta(days=10 + index),
                    "salary_budget_min": Decimal("350000.00") + Decimal(index * 50000),
                    "salary_budget_max": Decimal("650000.00") + Decimal(index * 75000),
                    "recruitment_budget": Decimal("1000000.00") + Decimal(index * 200000),
                    "actual_recruitment_cost": Decimal("850000.00") + Decimal(index * 150000),
                    "minimum_qualification": "Uganda Certificate of Education or equivalent.",
                    "experience_required": "Prior security experience preferred.",
                    "job_description": "Recruit qualified, disciplined personnel for client site deployment.",
                    "approval_notes": "Approved for active recruitment.",
                    "status": models.RecruitmentRequisition.RequisitionStatus.OPEN,
                },
            )
            requisitions.append(requisition)

        for index in range(1, 6):
            application, _created = models.RecruitmentApplication.objects.update_or_create(
                requisition=requisitions[(index - 1) % len(requisitions)],
                phone_number=f"07880000{index}",
                defaults={
                    "first_name": f"Applicant{index}",
                    "last_name": "Candidate",
                    "gender": ["Male", "Female", "Male", "Female", "Male"][index - 1],
                    "email": f"applicant{index}@demo.test",
                    "national_id": f"RC-NIN-{index:04d}",
                    "address": f"Applicant address {index}, Kampala",
                    "application_source": [
                        models.RecruitmentApplication.ApplicationSource.PHYSICAL,
                        models.RecruitmentApplication.ApplicationSource.ONLINE,
                        models.RecruitmentApplication.ApplicationSource.REFERRAL,
                        models.RecruitmentApplication.ApplicationSource.ONLINE,
                        models.RecruitmentApplication.ApplicationSource.PHYSICAL,
                    ][index - 1],
                    "date_received": today - timedelta(days=8 + index),
                    "online_profile_url": f"https://jobs.example.test/applicant-{index}" if index in {2, 4} else "",
                    "highest_qualification": "UACE",
                    "years_experience": Decimal(index),
                    "current_employer": "Demo Previous Employer",
                    "expected_salary": Decimal("500000.00") + Decimal(index * 25000),
                    "screening_score": 65 + index,
                    "police_clearance_no": f"PC-{index:04d}" if index % 2 else "",
                    "background_check_status": "Pending",
                    "medical_check_status": "Pending",
                    "reference_check_status": "Pending",
                    "status": models.RecruitmentApplication.ApplicationStatus.SHORTLISTED,
                    "notes": "Demo recruitment application.",
                },
            )
            models.RecruitmentInterview.objects.update_or_create(
                application=application,
                interview_type=models.RecruitmentInterview.InterviewType.ONLINE
                if application.application_source == models.RecruitmentApplication.ApplicationSource.ONLINE
                else models.RecruitmentInterview.InterviewType.PHYSICAL,
                defaults={
                    "scheduled_at": timezone.now() + timedelta(days=index),
                    "venue_or_link": "https://meet.example.test/recruitment" if index in {2, 4} else "Head Office Boardroom",
                    "interviewer": employees[5],
                    "score": 70 + index,
                    "recommendation": models.RecruitmentInterview.InterviewRecommendation.RECOMMENDED,
                    "feedback": "Candidate meets the minimum role requirements.",
                    "status": models.StatusChoices.APPROVED,
                },
            )
            if index <= 2:
                models.JobOffer.objects.update_or_create(
                    application=application,
                    defaults={
                        "offered_position": application.requisition.position,
                        "offer_date": today,
                        "expected_start_date": today + timedelta(days=14 + index),
                        "salary_offer": Decimal("550000.00") + Decimal(index * 50000),
                        "contract_type": "Full-time",
                        "status": models.JobOffer.OfferStatus.SENT,
                        "notes": "Offer pending candidate confirmation.",
                    },
                )

    def create_attendance(self, schedules, employees, shifts, today):
        for index, schedule in enumerate(schedules):
            models.Attendance.objects.update_or_create(
                employee=employees[index],
                date=today - timedelta(days=index),
                defaults={
                    "schedule": schedule,
                    "shift": shifts[index],
                    "time_in": time(8, 0),
                    "time_out": time(17, 0),
                    "status": "Present",
                    "remarks": "Demo attendance record.",
                },
            )

    def create_leaves(self, employees, today):
        for index, employee in enumerate(employees[:5], start=1):
            models.Leave.objects.update_or_create(
                employee=employee,
                start_date=today + timedelta(days=10 + index),
                defaults={
                    "leave_type": ["Annual", "Sick", "Compassionate", "Study", "Unpaid"][index - 1],
                    "end_date": today + timedelta(days=12 + index),
                    "days": 3,
                    "reason": "Demo leave request.",
                    "approval_status": models.StatusChoices.PENDING,
                    "approved_by": employees[5],
                },
            )

    def create_disciplinary_actions(self, employees, today):
        for index, employee in enumerate(employees[:5], start=1):
            models.DisciplinaryAction.objects.update_or_create(
                employee=employee,
                action_type=f"Demo Action {index}",
                action_date=today - timedelta(days=5 + index),
                defaults={
                    "description": "Demo disciplinary note.",
                    "penalty": ["Warning", "Counselling", "Retraining", "Written Warning", "Review"][index - 1],
                    "status": models.StatusChoices.PENDING,
                    "approved_by": employees[5],
                },
            )

    def create_performance_evaluations(self, employees, today):
        for index, employee in enumerate(employees[:5], start=1):
            models.PerformanceEvaluation.objects.update_or_create(
                employee=employee,
                eval_date=today - timedelta(days=15 + index),
                defaults={
                    "rating": index if index <= 5 else 5,
                    "comments": "Demo performance evaluation.",
                    "evaluated_by": employees[5],
                },
            )

    def create_documents(self, employees, today):
        for index, employee in enumerate(employees[:5], start=1):
            models.Document.objects.update_or_create(
                employee=employee,
                doc_type=f"Demo Document {index}",
                defaults={
                    "file_path": f"employee_documents/demo_document_{index}.pdf",
                    "issue_date": today - timedelta(days=120),
                    "expiry_date": today + timedelta(days=365),
                },
            )

    def create_salaries(self, employees, today):
        for index, employee in enumerate(employees[:5], start=1):
            models.Salary.objects.update_or_create(
                employee=employee,
                pay_period_start=date(today.year, today.month, 1),
                defaults={
                    "pay_period_end": date(today.year, today.month, 28),
                    "basic_salary": Decimal("500000.00") + Decimal(index * 50000),
                    "allowances": Decimal("50000.00"),
                    "deductions": Decimal("10000.00"),
                    "overtime_pay": Decimal("20000.00"),
                    "bonus": Decimal("15000.00"),
                    "payment_date": today,
                    "payment_method": "Bank Transfer",
                    "status": models.StatusChoices.PAID,
                },
            )

    def create_advances(self, employees, today):
        for index, employee in enumerate(employees[:5], start=1):
            models.Advance.objects.update_or_create(
                employee=employee,
                request_date=today - timedelta(days=index),
                defaults={
                    "amount_requested": Decimal("100000.00") + Decimal(index * 25000),
                    "purpose": "Demo salary advance.",
                    "approval_status": models.StatusChoices.APPROVED,
                    "approved_by": employees[5],
                    "disbursement_date": today,
                    "repayment_status": models.StatusChoices.PENDING,
                },
            )

    def create_invoices(self, clients, today):
        invoices = []
        for index, client in enumerate(clients, start=1):
            invoice, _created = models.Invoice.objects.update_or_create(
                invoice_number=f"DEMO-INV-{index:04d}",
                defaults={
                    "client": client,
                    "invoice_date": today - timedelta(days=index),
                    "due_date": today + timedelta(days=30),
                    "total_amount": Decimal("1500000.00") + Decimal(index * 100000),
                    "paid_amount": Decimal("500000.00"),
                    "status": models.StatusChoices.UNPAID,
                },
            )
            invoices.append(invoice)
        return invoices

    def create_payments(self, invoices, employees, today):
        for index, invoice in enumerate(invoices, start=1):
            models.Payment.objects.update_or_create(
                transaction_ref=f"DEMO-PAY-{index:04d}",
                defaults={
                    "invoice": invoice,
                    "employee": employees[index - 1],
                    "payment_date": today - timedelta(days=index),
                    "amount": Decimal("500000.00"),
                    "payment_method": "Mobile Money" if index % 2 else "Bank Transfer",
                    "remarks": "Demo payment.",
                },
            )

    def create_budgets(self):
        data = [
            (2026, models.DepartmentChoices.OPERATIONS, "Demo Patrol Equipment"),
            (2026, models.DepartmentChoices.OPERATIONS, "Demo Vehicle Fuel"),
            (2026, models.DepartmentChoices.HUMAN_RESOURCE, "Demo Training"),
            (2026, models.DepartmentChoices.FINANCE, "Demo Audit"),
            (2026, models.DepartmentChoices.ADMIN, "Demo Office Supplies"),
        ]
        for index, (year, department, category) in enumerate(data, start=1):
            models.Budget.objects.update_or_create(
                year=year,
                department=department,
                category=category,
                defaults={
                    "allocated_amount": Decimal("3000000.00") + Decimal(index * 250000),
                    "spent_amount": Decimal("500000.00") + Decimal(index * 100000),
                },
            )

    def create_expenses(self, employees, today):
        for index in range(1, 6):
            models.Expense.objects.update_or_create(
                receipt_no=f"DEMO-RCPT-{index:04d}",
                defaults={
                    "expense_date": today - timedelta(days=index),
                    "category": ["Fuel", "Uniforms", "Training", "Repairs", "Stationery"][index - 1],
                    "description": "Demo expense.",
                    "amount": Decimal("150000.00") + Decimal(index * 30000),
                    "approved_by": employees[5],
                    "remarks": "Demo expense record.",
                },
            )
