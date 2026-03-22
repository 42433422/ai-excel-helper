# -*- coding: utf-8 -*-
"""
Skill Maker Skill Module

Helps create new SKILLs for the workspace.
"""

import os
import re
from typing import Any, Dict, List, Optional


def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


def get_skills_dir():
    return os.path.join(get_base_dir(), ".trae", "skills")


def list_existing_skills() -> List[Dict[str, str]]:
    skills_dir = get_skills_dir()
    if not os.path.exists(skills_dir):
        return []

    skills = []
    for name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, name)
        if os.path.isdir(skill_path):
            skill_md = os.path.join(skill_path, "SKILL.md")
            skills.append({
                'name': name,
                'path': skill_path,
                'has_skill_md': os.path.exists(skill_md)
            })
    return skills


def create_skill_directory(skill_name: str) -> Dict[str, Any]:
    skills_dir = get_skills_dir()
    skill_path = os.path.join(skills_dir, skill_name)

    if os.path.exists(skill_path):
        return {
            'success': False,
            'message': f'Skill "{skill_name}" already exists at {skill_path}'
        }

    os.makedirs(skill_path, exist_ok=True)
    return {
        'success': True,
        'message': f'Skill directory created: {skill_path}',
        'path': skill_path
    }


def create_skill_md(skill_name: str, description: str, content: str = None) -> Dict[str, Any]:
    skills_dir = get_skills_dir()
    skill_path = os.path.join(skills_dir, skill_name)

    if not os.path.exists(skill_path):
        os.makedirs(skill_path, exist_ok=True)

    skill_md_path = os.path.join(skill_path, "SKILL.md")

    if content is None:
        content = f"""---
name: "{skill_name}"
description: "{description}"
---

# {skill_name.replace('-', ' ').title()} Skill

{description}

## Usage

Describe how to use this skill here.
"""

    with open(skill_md_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        'success': True,
        'message': f'SKILL.md created at {skill_md_path}',
        'path': skill_md_path
    }


def create_skill(
    skill_name: str,
    description: str,
    content: str = None,
    create_init: bool = False,
    create_impl: bool = False,
    impl_content: str = None
) -> Dict[str, Any]:
    result = create_skill_directory(skill_name)
    if not result['success']:
        return result

    result = create_skill_md(skill_name, description, content)
    if not result['success']:
        return result

    files_created = [result['path']]

    if create_init:
        init_path = os.path.join(get_skills_dir(), skill_name, "__init__.py")
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(f"# -*- coding: utf-8 -*-\n")
            f.write(f'"""{skill_name} Skill Module"""\n\n')
            f.write(f"# Add your exports here\n")
        files_created.append(init_path)

    if create_impl:
        impl_name = skill_name.replace('-', '_')
        impl_path = os.path.join(get_skills_dir(), skill_name, f"{impl_name}.py")

        if impl_content is None:
            impl_content = f"""# -*- coding: utf-8 -*-
\"\"\""
{skill_name.replace('-', ' ').title()} Skill Module
\"\"\"

def get_{impl_name}_skill():
    return {{
        'name': '{skill_name}',
        'description': '{description}',
        'functions': {{}}
    }}
"""

        with open(impl_path, 'w', encoding='utf-8') as f:
            f.write(impl_content)
        files_created.append(impl_path)

    return {
        'success': True,
        'message': f'Skill "{skill_name}" created successfully',
        'files_created': files_created
    }


def validate_skill(skill_name: str) -> Dict[str, Any]:
    skills_dir = get_skills_dir()
    skill_path = os.path.join(skills_dir, skill_name)

    if not os.path.exists(skill_path):
        return {
            'valid': False,
            'message': f'Skill "{skill_name}" does not exist'
        }

    issues = []
    warnings = []

    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.exists(skill_md):
        issues.append("Missing SKILL.md file")

    if os.path.exists(skill_md):
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        if not re.search(r'^name:\s*["\']?\w+["\']?\s*$', content, re.MULTILINE):
            warnings.append("Missing or invalid 'name' field in frontmatter")

        if not re.search(r'^description:\s*.+\s*$', content, re.MULTILINE):
            warnings.append("Missing or invalid 'description' field in frontmatter")

    __init__ = os.path.join(skill_path, "__init__.py")
    if not os.path.exists(__init__):
        warnings.append("Missing __init__.py file")

    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'skill_path': skill_path
    }


def get_skill_maker_skill():
    return {
        'name': 'skill-maker',
        'description': 'Helps create new SKILLs for the workspace',
        'functions': {
            'list_existing_skills': list_existing_skills,
            'create_skill': create_skill,
            'create_skill_directory': create_skill_directory,
            'create_skill_md': create_skill_md,
            'validate_skill': validate_skill,
        }
    }