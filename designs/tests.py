from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

from .models import Design, CustomizationOption
from .utils import (
    generate_design_id,
    get_designer_statistics,
    check_material_requirements,
    calculate_customization_price
)
from accounts.models import Designer, FactoryPartner, FactoryDetails
from inventory.models import TextileWaste, Dimensions

User = get_user_model()

class DesignUtilsUnitTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test user for designer
        self.designer_user = User.objects.create_user(
            username="testdesigner",
            email="designer@example.com",
            password="testpass123"
        )
        
        # Create designer
        self.designer = Designer.objects.create(
            user=self.designer_user
        )
        
        # Create a factory user, factory details, and factory partner for textile waste
        self.factory_user = User.objects.create_user(
            username="factoryuser",
            email="factory@example.com",
            password="testpass123"
        )
        self.factory_details = FactoryDetails.objects.create(
            factory_name="Test Factory",
            location="Test City",
            production_capacity=1000
        )
        self.factory_partner = FactoryPartner.objects.create(
            user=self.factory_user,
            factory_details=self.factory_details
        )
        
        # Create dimensions objects - create a unique one for each textile waste
        self.dimensions1 = Dimensions.objects.create(length=1.0, width=1.0, unit="m")
        self.dimensions2 = Dimensions.objects.create(length=1.5, width=1.5, unit="m")
        self.dimensions3 = Dimensions.objects.create(length=2.0, width=2.0, unit="m")
        
        # Create textile waste materials with all required fields and unique dimensions
        self.material1 = TextileWaste.objects.create(
            waste_id="WST-1",
            type="Fabric", 
            material="Cotton", 
            quantity=100,
            unit="kg", 
            color="White",
            dimensions=self.dimensions1,
            quality_grade="GOOD", 
            status="AVAILABLE",
            factory=self.factory_partner
        )
        
        self.material2 = TextileWaste.objects.create(
            waste_id="WST-2",
            type="Fabric", 
            material="Polyester", 
            quantity=50,
            unit="kg", 
            color="White",
            dimensions=self.dimensions2,
            quality_grade="GOOD", 
            status="AVAILABLE",
            factory=self.factory_partner
        )
        
        self.material3 = TextileWaste.objects.create(
            waste_id="WST-3",
            type="Fabric", 
            material="Linen", 
            quantity=0,
            unit="kg", 
            color="White",
            dimensions=self.dimensions3,
            quality_grade="GOOD", 
            status="OUT_OF_STOCK",
            factory=self.factory_partner
        )
        
        # Create designs
        self.design1 = Design.objects.create(
            design_id=generate_design_id(),
            name="Summer Dress",
            description="Beautiful summer dress made from recycled materials",
            designer=self.designer,
            price=Decimal('150.00'),
            status="PUBLISHED"
        )
        self.design1.required_materials.add(self.material1)
        
        self.design2 = Design.objects.create(
            design_id=generate_design_id(),
            name="Winter Sweater",
            description="Warm winter sweater made from recycled wool",
            designer=self.designer,
            price=Decimal('200.00'),
            status="PUBLISHED"
        )
        self.design2.required_materials.add(self.material2)
        
        self.design3 = Design.objects.create(
            design_id=generate_design_id(),
            name="Linen Trousers",
            description="Comfortable linen trousers",
            designer=self.designer,
            price=Decimal('120.00'),
            status="DRAFT"
        )
        self.design3.required_materials.add(self.material3)
        
        # Create customization options
        self.color_option = CustomizationOption.objects.create(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            name="color",
            type="COLOR",
            available_choices=["red", "blue", "green"],
            price_impact={"red": 10, "blue": 5, "green": 0},
            design=self.design1
        )
        
        self.size_option = CustomizationOption.objects.create(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            name="size",
            type="SIZE",
            available_choices=["small", "medium", "large"],
            price_impact={"small": 0, "medium": 5, "large": 10},
            design=self.design1
        )
    
    def test_generate_design_id(self):
        """Test design ID generation"""
        design_id = generate_design_id()
        self.assertTrue(design_id.startswith("DSG-"))
        self.assertEqual(len(design_id), 12)  # "DSG-" + 8 chars
    
    def test_get_designer_statistics(self):
        """Test getting designer statistics"""
        stats = get_designer_statistics(self.designer)
        
        self.assertEqual(stats["total_designs"], 3)
        self.assertEqual(stats["published_designs"], 2)
        self.assertEqual(stats["average_price"], Decimal('175.00'))  # (150 + 200) / 2
        self.assertEqual(stats["customizable_designs"], 1)  # Only design1 has customization options
    
    def test_check_material_requirements_available(self):
        """Test checking material requirements when all materials are available"""
        self.assertTrue(check_material_requirements(self.design1.design_id))
        self.assertTrue(check_material_requirements(self.design2.design_id))
    
    def test_check_material_requirements_unavailable(self):
        """Test checking material requirements when materials are unavailable"""
        self.assertFalse(check_material_requirements(self.design3.design_id))
    
    def test_check_material_requirements_nonexistent_design(self):
        """Test checking material requirements for a nonexistent design"""
        self.assertFalse(check_material_requirements("DSG-NONEXISTENT"))
    
    def test_calculate_customization_price(self):
        """Test calculating price with customizations"""
        # Base price (150) + color:red (10) + size:medium (5)
        customizations = {"color": "red", "size": "medium"}
        result = calculate_customization_price(self.design1.design_id, customizations)
        self.assertEqual(result, Decimal('165.00'))
    
    def test_calculate_customization_price_nonexistent_design(self):
        """Test calculating price for nonexistent design"""
        customizations = {"color": "red"}
        result = calculate_customization_price("DSG-NONEXISTENT", customizations)
        self.assertIsNone(result)


class DesignModelUnitTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test user for designer
        self.designer_user = User.objects.create_user(
            username="testdesigner",
            email="designer@example.com",
            password="testpass123"
        )
        
        # Create designer
        self.designer = Designer.objects.create(
            user=self.designer_user
        )
        
        # Create a factory user, factory details, and factory partner for textile waste
        self.factory_user = User.objects.create_user(
            username="factoryuser2",
            email="factory2@example.com",
            password="testpass123"
        )
        self.factory_details = FactoryDetails.objects.create(
            factory_name="Test Factory 2",
            location="Test City 2",
            production_capacity=1000
        )
        self.factory_partner = FactoryPartner.objects.create(
            user=self.factory_user,
            factory_details=self.factory_details
        )
        
        # Create separate dimensions objects for each TextileWaste
        self.dimensions1 = Dimensions.objects.create(length=1.0, width=1.0, unit="m")
        self.dimensions2 = Dimensions.objects.create(length=1.2, width=1.2, unit="m")
        
        # Create textile waste materials with all required fields and unique dimensions
        self.material1 = TextileWaste.objects.create(
            waste_id="WST-A",
            type="Fabric",
            material="Cotton",
            quantity=100,
            unit="kg",
            color="White",
            dimensions=self.dimensions1,
            quality_grade="GOOD",
            status="AVAILABLE",
            factory=self.factory_partner
        )
        self.material2 = TextileWaste.objects.create(
            waste_id="WST-B",
            type="Fabric",
            material="Polyester",
            quantity=50,
            unit="kg",
            color="White",
            dimensions=self.dimensions2,
            quality_grade="GOOD",
            status="AVAILABLE",
            factory=self.factory_partner
        )
        
        # Create design
        self.design = Design.objects.create(
            design_id=f"DSG-{uuid.uuid4().hex[:8].upper()}",
            name="Summer Dress",
            description="Beautiful summer dress made from recycled materials",
            designer=self.designer,
            price=Decimal('150.00'),
            status="PUBLISHED"
        )
        self.design.required_materials.add(self.material1, self.material2)
        
        # Create customization options
        self.color_option = CustomizationOption.objects.create(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            name="color",
            type="COLOR",
            available_choices=["red", "blue", "green"],
            price_impact={"red": 10, "blue": 5, "green": 0},
            design=self.design
        )
    
    def test_is_customizable(self):
        """Test is_customizable method"""
        self.assertTrue(self.design.is_customizable())
        
        # Create design without customization options
        design_without_options = Design.objects.create(
            design_id=f"DSG-{uuid.uuid4().hex[:8].upper()}",
            name="Simple Dress",
            description="Simple dress without customization options",
            designer=self.designer,
            price=Decimal('100.00'),
            status="PUBLISHED"
        )
        
        self.assertFalse(design_without_options.is_customizable())
    
    def test_get_available_quantity(self):
        """Test get_available_quantity method"""
        # The minimum quantity across materials is 50 (from material2)
        self.assertEqual(self.design.get_available_quantity(), 50)
        
        # Create design without materials
        design_without_materials = Design.objects.create(
            design_id=f"DSG-{uuid.uuid4().hex[:8].upper()}",
            name="Simple Dress",
            description="Simple dress without materials",
            designer=self.designer,
            price=Decimal('100.00'),
            status="PUBLISHED"
        )
        
        # Should return default value (12) when no materials
        self.assertEqual(design_without_materials.get_available_quantity(), 12)


class CustomizationOptionModelUnitTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test user for designer
        self.designer_user = User.objects.create_user(
            username="testdesigner",
            email="designer@example.com",
            password="testpass123"
        )
        
        # Create designer
        self.designer = Designer.objects.create(
            user=self.designer_user
        )
        
        # Create design
        self.design = Design.objects.create(
            design_id=f"DSG-{uuid.uuid4().hex[:8].upper()}",
            name="Summer Dress",
            description="Beautiful summer dress made from recycled materials",
            designer=self.designer,
            price=Decimal('100.00'),
            status="PUBLISHED"
        )
        
        # Create customization options
        self.color_option = CustomizationOption.objects.create(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            name="color",
            type="COLOR",
            available_choices=["red", "blue", "green"],
            price_impact={"red": 10, "blue": 5, "green": 0},
            design=self.design
        )
        
        self.size_option = CustomizationOption.objects.create(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            name="size",
            type="SIZE",
            available_choices=["small", "medium", "large"],
            price_impact={"has_impact": True},
            design=self.design
        )
        
        self.empty_option = CustomizationOption.objects.create(
            option_id=f"OPT-{uuid.uuid4().hex[:8].upper()}",
            name="material",
            type="MATERIAL",
            available_choices=[],
            price_impact={},
            design=self.design
        )
    
    def test_choices_property_with_values(self):
        """Test choices property returns available choices when they exist"""
        self.assertEqual(self.color_option.choices, ["red", "blue", "green"])
    
    def test_choices_property_empty_with_defaults(self):
        """Test choices property returns default values for empty available_choices"""
        # Size should use defaults based on type
        self.assertEqual(self.empty_option.choices, [])
    
    def test_additional_cost_with_impact(self):
        """Test additional_cost property for options with price impact"""
        # Size option has has_impact: True and type: SIZE (10%)
        self.assertEqual(self.size_option.additional_cost, Decimal('10.00'))  # 10% of 100
    
    def test_additional_cost_without_impact(self):
        """Test additional_cost property for options without price impact"""
        # Empty option has no price impact setting
        self.assertEqual(self.empty_option.additional_cost, Decimal('0.00'))


class DesignViewsModuleTest(TestCase):
    def setUp(self):
        """Set up test data for testing views"""
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin', 
            email='admin@example.com',
            password='adminpass',
            is_staff=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com', 
            password='regularpass'
        )
        
        # Create designer user
        self.designer_user = User.objects.create_user(
            username='designer',
            email='designer@example.com', 
            password='designerpass'
        )
        
        # Create approved designer profile
        self.designer = Designer.objects.create(
            user=self.designer_user,
            is_approved=True
        )
        # Ensure designer user has complete contact info
        from accounts.models import ContactInfo
        contact_info = ContactInfo.objects.create(address="123 Test St", phone="1234567890")
        self.designer_user.contact_info = contact_info
        self.designer_user.save()
        
        # Create unapproved designer user
        self.unapproved_designer_user = User.objects.create_user(
            username='unapproved',
            email='unapproved@example.com', 
            password='unapprovedpass'
        )
        
        # Create unapproved designer profile
        self.unapproved_designer = Designer.objects.create(
            user=self.unapproved_designer_user,
            is_approved=False
        )
        
        # Create factory details
        self.factory_details = FactoryDetails.objects.create(
            factory_name="Test Factory",
            location="Test Location",
            production_capacity=1000
        )
        
        # Create factory partner
        self.factory_partner = FactoryPartner.objects.create(
            user=self.admin_user,
            factory_details=self.factory_details
        )
        
        # Create dimensions
        self.dimensions = Dimensions.objects.create(
            length=1.0, 
            width=1.0, 
            unit="m"
        )
        
        # Create material
        self.material = TextileWaste.objects.create(
            waste_id="TEST-MAT-001",
            type="Fabric",
            material="Cotton",
            quantity=100,
            unit="kg",
            color="White",
            dimensions=self.dimensions,
            quality_grade="GOOD",
            status="AVAILABLE",
            factory=self.factory_partner
        )
        
        # Create published design
        self.published_design = Design.objects.create(
            design_id="TEST-PUB-001",
            name="Published Design",
            description="This is a published design",
            designer=self.designer,
            price=Decimal('150.00'),
            status="PUBLISHED"
        )
        self.published_design.required_materials.add(self.material)
        
        # Create draft design
        self.draft_design = Design.objects.create(
            design_id="TEST-DFT-001",
            name="Draft Design",
            description="This is a draft design",
            designer=self.designer,
            price=Decimal('120.00'),
            status="DRAFT"
        )
        
        # Create customization option
        self.customization = CustomizationOption.objects.create(
            option_id="TEST-OPT-001",
            name="color",
            type="COLOR",
            available_choices=["red", "blue", "green"],
            price_impact={"red": 10, "blue": 5, "green": 0},
            design=self.published_design
        )
        
        # Setup client
        self.client = Client()
    
    def test_design_list_view(self):
        """Test the design_list view shows published designs"""
        response = self.client.get(reverse('designs:design_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'designs/design_list.html')
        self.assertIn('designs', response.context)
        self.assertIn(self.published_design, response.context['designs'])
        self.assertNotIn(self.draft_design, response.context['designs'])
    
    def test_design_list_search(self):
        """Test the design_list search functionality"""
        response = self.client.get(f"{reverse('designs:design_list')}?search=Published")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.published_design, response.context['designs'])
        
        response = self.client.get(f"{reverse('designs:design_list')}?search=Nonexistent")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.published_design, response.context['designs'])
    
    def test_design_detail_view_published(self):
        """Test the design_detail view for published designs"""
        response = self.client.get(reverse('designs:design_detail', kwargs={'design_id': self.published_design.design_id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'designs/design_detail.html')
        self.assertEqual(response.context['design'], self.published_design)
        self.assertIn('materials', response.context)
    
    def test_design_detail_view_draft_unauthenticated(self):
        """Test unauthorized users cannot view draft designs"""
        response = self.client.get(reverse('designs:design_detail', kwargs={'design_id': self.draft_design.design_id}))
        self.assertEqual(response.status_code, 404)
    
    def test_design_detail_view_draft_owner(self):
        """Test design owner can view their draft designs"""
        self.client.login(username='designer', password='designerpass')
        response = self.client.get(reverse('designs:design_detail', kwargs={'design_id': self.draft_design.design_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['design'], self.draft_design)
    
    def test_designer_dashboard_approved(self):
        """Test approved designer can access dashboard"""
        self.client.login(username='designer', password='designerpass')
        response = self.client.get(reverse('designs:designer_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'designs/designer_dashboard.html')
        self.assertIn('designs', response.context)
        self.assertIn('total_designs', response.context)
        self.assertIn('published_designs', response.context)
    
    def test_designer_dashboard_unapproved(self):
        """Test unapproved designer is redirected from dashboard"""
        self.client.login(username='unapproved', password='unapprovedpass')
        response = self.client.get(reverse('designs:designer_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect expected
    
    def test_designer_dashboard_not_designer(self):
        """Test non-designer user cannot access dashboard"""
        self.client.login(username='regular', password='regularpass')
        response = self.client.get(reverse('designs:designer_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect expected
    
    def test_design_create_view_get(self):
        """Test the design_create GET view for approved designer"""
        self.client.login(username='designer', password='designerpass')
        response = self.client.get(reverse('designs:design_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'designs/design_form.html')
        self.assertIn('form', response.context)
        self.assertIn('options_formset', response.context)
        self.assertIn('materials_formset', response.context)
    
    def test_design_create_unauthorized(self):
        """Test unauthorized users cannot access design creation"""
        response = self.client.get(reverse('designs:design_create'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Regular user cannot create designs
        self.client.login(username='regular', password='regularpass')
        response = self.client.get(reverse('designs:design_create'))
        self.assertEqual(response.status_code, 302)  # Redirect expected
        
        # Unapproved designer cannot create designs
        self.client.login(username='unapproved', password='unapprovedpass')
        response = self.client.get(reverse('designs:design_create'))
        self.assertEqual(response.status_code, 302)  # Redirect expected
    
    def test_design_edit_view_get(self):
        """Test the design_edit GET view for design owner"""
        self.client.login(username='designer', password='designerpass')
        response = self.client.get(reverse('designs:design_edit', kwargs={'design_id': self.published_design.design_id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'designs/design_form.html')
        self.assertIn('form', response.context)
        self.assertIn('design', response.context)
    
    def test_design_edit_unauthorized(self):
        """Test unauthorized users cannot edit designs"""
        # Unauthenticated user
        response = self.client.get(reverse('designs:design_edit', kwargs={'design_id': self.published_design.design_id}))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Non-owner cannot edit
        self.client.login(username='regular', password='regularpass')
        response = self.client.get(reverse('designs:design_edit', kwargs={'design_id': self.published_design.design_id}))
        self.assertEqual(response.status_code, 302)  # Redirect expected
    
    def test_design_delete_view_get(self):
        """Test the design_delete GET view shows confirmation page"""
        self.client.login(username='designer', password='designerpass')
        response = self.client.get(reverse('designs:design_delete', kwargs={'design_id': self.published_design.design_id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'designs/design_confirm_delete.html')
        self.assertEqual(response.context['design'], self.published_design)
    
    def test_design_delete_view_post(self):
        """Test the design_delete POST view actually deletes the design"""
        self.client.login(username='designer', password='designerpass')
        response = self.client.post(reverse('designs:design_delete', kwargs={'design_id': self.published_design.design_id}))
        self.assertEqual(response.status_code, 302)  # Redirect after delete
        
        # Check design is deleted (marked as deleted)
        updated_design = Design.objects.get(design_id=self.published_design.design_id)
        self.assertEqual(updated_design.status, "DELETED")
    
    def test_design_customize_view_get(self):
        """Test the design_customize GET view for a published design"""
        self.client.login(username='regular', password='regularpass')
        response = self.client.get(reverse('designs:design_customize', kwargs={'design_id': self.published_design.design_id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'designs/design_customize.html')
        self.assertEqual(response.context['design'], self.published_design)
        self.assertIn('customization_options', response.context)
    
    def test_design_customize_post(self):
        """Test the design_customize POST view with options selection"""
        self.client.login(username='regular', password='regularpass')
        response = self.client.post(
            reverse('designs:design_customize', kwargs={'design_id': self.published_design.design_id}),
            data={f'option_{self.customization.id}': 'red'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect to order creation
        
        # Check session has the customizations saved
        self.assertIn('design_customizations', self.client.session)
        self.assertEqual(self.client.session['design_customizations']['design_id'], self.published_design.design_id)
        self.assertEqual(self.client.session['design_customizations']['options']['color'], 'red')
    
    def test_design_customize_unauthorized_draft(self):
        """Test users cannot customize draft designs"""
        self.client.login(username='regular', password='regularpass')
        response = self.client.get(reverse('designs:design_customize', kwargs={'design_id': self.draft_design.design_id}))
        self.assertEqual(response.status_code, 404)  # Draft design not found
