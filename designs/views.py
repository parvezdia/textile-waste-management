from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django import forms
from django.forms import inlineformset_factory
import uuid

from inventory.models import TextileWaste, Dimensions
from .decorators import approved_designer_required, can_manage_design
from .forms import CustomizationOptionForm, DesignForm, MaterialRequirementForm
from .models import Design, CustomizationOption


def design_list(request):
    designs = Design.objects.filter(status="PUBLISHED")
    paginator = Paginator(designs, 12)  # Show 12 designs per page
    page = request.GET.get("page")
    designs = paginator.get_page(page)
    return render(request, "designs/design_list.html", {"designs": designs})


def design_detail(request, design_id):
    design = get_object_or_404(Design, design_id=design_id, status="PUBLISHED")
    return render(request, "designs/design_detail.html", {"design": design})


@login_required
@approved_designer_required
def designer_dashboard(request):
    # First check if profile is complete
    contact_info = request.user.contact_info
    if not all([
        contact_info and contact_info.address and contact_info.phone
    ]):
        messages.warning(request, "Please complete your profile setup to access the dashboard.")
        return redirect("accounts:profile_setup")
    
    designs = Design.objects.filter(designer__user=request.user)
    context = {
        "designs": designs,
        "total_designs": designs.count(),
        "published_designs": designs.filter(status="PUBLISHED").count(),
        "draft_designs": designs.filter(status="DRAFT").count(),
        "archived_designs": designs.filter(status="ARCHIVED").count(),
    }
    return render(request, "designs/designer_dashboard.html", context)


@login_required
@approved_designer_required
def design_create(request):
    CustomizationOptionFormSet = inlineformset_factory(
        Design, 
        CustomizationOption,
        form=CustomizationOptionForm,
        extra=1,
        can_delete=True,
        fields=['name', 'type', 'available_choices', 'price_impact']
    )
    
    MaterialRequirementFormSet = forms.formset_factory(
        MaterialRequirementForm,
        extra=1,
        can_delete=True
    )
    
    if request.method == "POST":
        form = DesignForm(request.POST, request.FILES)
        materials_formset = MaterialRequirementFormSet(request.POST, prefix='materials')
        options_formset = CustomizationOptionFormSet(request.POST, prefix='options')
        
        forms_valid = form.is_valid()
        materials_valid = materials_formset.is_valid()
        options_valid = True
        
        if form.is_valid():
            is_customizable = form.cleaned_data.get('is_customizable', False)
            if is_customizable:
                options_valid = options_formset.is_valid()
        
        if forms_valid and materials_valid and options_valid:
            try:
                from django.db import transaction
                with transaction.atomic():
                    # Create design instance
                    design = form.save(commit=False)
                    design.designer = request.user.designer
                    if not design.design_id:
                        design.design_id = f"DES_{uuid.uuid4().hex[:8]}"
                    design.save()
                    form.save_m2m()  # Save many-to-many relationships
                    
                    # Save materials with their requirements
                    for material_form in materials_formset:
                        if material_form.is_valid() and not material_form.cleaned_data.get('DELETE', False):
                            material_data = material_form.cleaned_data
                            # Create dimensions instance
                            dimensions = Dimensions.objects.create(
                                length=material_data['length'],
                                width=material_data['width'],
                                unit=material_data['unit']
                            )
                            # Create material requirement
                            material = TextileWaste.objects.create(
                                waste_id=f"DESIGN_REQ_{uuid.uuid4().hex[:8]}",
                                material=material_data['material'],
                                type=material_data['type'],
                                quantity=material_data['quantity_required'],
                                color=material_data.get('color'),
                                quality_grade=material_data['quality_grade'],
                                dimensions=dimensions,
                                status="PENDING_REVIEW"
                            )
                            design.required_materials.add(material)
                    
                    # Save customization options if enabled
                    if form.cleaned_data.get('is_customizable', False):
                        options_formset.instance = design
                        options_formset.save()
                
                messages.success(request, "Design created successfully!")
                return redirect("designs:design_detail", design_id=design.design_id)
                
            except Exception as e:
                # Roll back any partial changes
                messages.error(request, f"Error creating design: {str(e)}")
        else:
            if not forms_valid:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            
            if not materials_valid:
                for form_errors in materials_formset.errors:
                    for field, errors in form_errors.items():
                        messages.error(request, f"Material {field}: {', '.join(errors)}")
            
            if form.cleaned_data.get('is_customizable', False) and not options_valid:
                for form_errors in options_formset.errors:
                    for field, errors in form_errors.items():
                        messages.error(request, f"Customization {field}: {', '.join(errors)}")
    else:
        form = DesignForm()
        options_formset = CustomizationOptionFormSet(prefix='options')
        materials_formset = MaterialRequirementFormSet(prefix='materials')
    
    return render(
        request,
        "designs/design_form.html",
        {
            "form": form,
            "options_formset": options_formset,
            "materials_formset": materials_formset,
            "action": "Create"
        }
    )


@login_required
@can_manage_design
def design_edit(request, design_id):
    design = get_object_or_404(Design, design_id=design_id, designer__user=request.user)
    
    CustomizationOptionFormSet = inlineformset_factory(
        Design,
        CustomizationOption,
        form=CustomizationOptionForm,
        extra=1,
        can_delete=True,
        fields=['name', 'type', 'available_choices', 'price_impact']
    )
    
    MaterialRequirementFormSet = forms.formset_factory(
        MaterialRequirementForm,
        extra=1,
        can_delete=True
    )
    
    if request.method == "POST":
        form = DesignForm(request.POST, request.FILES, instance=design)
        options_formset = CustomizationOptionFormSet(request.POST, prefix='options', instance=design)
        materials_formset = MaterialRequirementFormSet(
            request.POST, 
            prefix='materials',
            initial=[{
                'material': material.material,
                'type': material.type,
                'quantity_required': material.quantity,
                'color': material.color,
                'quality_grade': material.quality_grade,
                'length': material.dimensions.length if material.dimensions else None,
                'width': material.dimensions.width if material.dimensions else None,
                'unit': material.dimensions.unit if material.dimensions else 'm'
            } for material in design.required_materials.all()]
        )
        
        if form.is_valid() and materials_formset.is_valid() and (not form.cleaned_data.get('is_customizable', False) or options_formset.is_valid()):
            form.save()
            
            # Update materials with their requirements
            design.required_materials.clear()  # Remove existing materials
            for material_form in materials_formset:
                if material_form.is_valid() and not material_form.cleaned_data.get('DELETE', False):
                    material_data = material_form.cleaned_data
                    # Create dimensions instance
                    dimensions = Dimensions.objects.create(
                        length=material_data['length'],
                        width=material_data['width'],
                        unit=material_data['unit']
                    )
                    # Create material requirement
                    material = TextileWaste.objects.create(
                        waste_id=f"DESIGN_REQ_{uuid.uuid4().hex[:8]}",
                        material=material_data['material'],
                        type=material_data['type'],
                        quantity=material_data['quantity_required'],
                        color=material_data.get('color'),
                        quality_grade=material_data['quality_grade'],
                        dimensions=dimensions,
                        status="PENDING_REVIEW"
                    )
                    design.required_materials.add(material)
            
            # Update customization options if enabled
            if form.cleaned_data.get('is_customizable', False):
                options_formset.save()
                
            messages.success(request, "Design updated successfully!")
            return redirect("designs:design_detail", design_id=design.design_id)
    else:
        form = DesignForm(instance=design)
        options_formset = CustomizationOptionFormSet(prefix='options', instance=design)
        materials_formset = MaterialRequirementFormSet(
            prefix='materials',
            initial=[{
                'material': material.material,
                'type': material.type,
                'quantity_required': material.quantity,
                'color': material.color,
                'quality_grade': material.quality_grade,
                'length': material.dimensions.length if material.dimensions else None,
                'width': material.dimensions.width if material.dimensions else None,
                'unit': material.dimensions.unit if material.dimensions else 'm'
            } for material in design.required_materials.all()]
        )
    
    return render(
        request,
        "designs/design_form.html",
        {
            "form": form,
            "options_formset": options_formset,
            "materials_formset": materials_formset,
            "action": "Edit",
            "design": design
        }
    )


@login_required
@can_manage_design
def design_delete(request, design_id):
    design = get_object_or_404(Design, design_id=design_id, designer__user=request.user)
    if request.method == "POST":
        design.status = "DELETED"
        design.save()
        messages.success(request, "Design deleted successfully!")
        return redirect("designs:design_list")
    return render(request, "designs/design_confirm_delete.html", {"design": design})
