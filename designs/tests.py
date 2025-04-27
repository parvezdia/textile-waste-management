from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

from .models import Design, Image, CustomizationOption
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
