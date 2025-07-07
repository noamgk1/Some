import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import base64


class JiraIssueManager:
    """
    מחלקה לניהול Issues בג'ירה - יצירה, עדכון, מחיקה וחיפוש
    """
    
    def __init__(self, base_url: str, username: str, token: str):
        """
        אתחול החיבור לג'ירה
        
        Args:
            base_url (str): כתובת הבסיס של ג'ירה (למשל: https://your-domain.atlassian.net)
            username (str): שם המשתמש או כתובת האימייל
            token (str): API Token מג'ירה
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.token = token
        self.api_url = f"{self.base_url}/rest/api/3"
        
        # הכנת headers עם אימות
        auth_string = f"{username}:{token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def test_connection(self) -> bool:
        """
        בדיקת חיבור לג'ירה
        
        Returns:
            bool: True אם החיבור תקין, False אחרת
        """
        try:
            response = requests.get(f"{self.api_url}/myself", headers=self.headers)
            if response.status_code == 200:
                user_info = response.json()
                print(f"חיבור מוצלח! מחובר כמשתמש: {user_info.get('displayName', 'לא ידוע')}")
                return True
            else:
                print(f"שגיאה בחיבור: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"שגיאה בחיבור: {str(e)}")
            return False
    
    def get_projects(self) -> List[Dict]:
        """
        קבלת רשימת כל הפרויקטים
        
        Returns:
            List[Dict]: רשימת הפרויקטים
        """
        try:
            response = requests.get(f"{self.api_url}/project", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"שגיאה בקבלת פרויקטים: {response.status_code}")
                return []
        except Exception as e:
            print(f"שגיאה: {str(e)}")
            return []
    
    def get_issue_types(self, project_key: str) -> List[Dict]:
        """
        קבלת סוגי Issues זמינים בפרויקט
        
        Args:
            project_key (str): מפתח הפרויקט
            
        Returns:
            List[Dict]: רשימת סוגי Issues
        """
        try:
            response = requests.get(
                f"{self.api_url}/project/{project_key}/statuses",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"שגיאה בקבלת סוגי Issues: {response.status_code}")
                return []
        except Exception as e:
            print(f"שגיאה: {str(e)}")
            return []

    def get_create_issue_metadata(self, project_key: str, issue_type: str = None) -> Dict:
        """
        קבלת מטא-דאטה לשדות יצירת Issue - כולל שדות חובה ואופציונליים
        
        Args:
            project_key (str): מפתח הפרויקט
            issue_type (str): סוג הIssue (אופציונלי)
            
        Returns:
            Dict: מטא-דאטה של שדות יצירת Issue
        """
        params = {
            'projectKeys': project_key,
            'expand': 'projects.issuetypes.fields'
        }
        
        if issue_type:
            params['issuetypeNames'] = issue_type
            
        try:
            response = requests.get(
                f"{self.api_url}/issue/createmeta",
                headers=self.headers,
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"שגיאה בקבלת מטא-דאטה: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"שגיאה: {str(e)}")
            return {}

    def get_fields_for_issue_type(self, project_key: str, issue_type: str) -> Dict:
        """
        קבלת שדות ספציפיים לסוג Issue מסוים
        
        Args:
            project_key (str): מפתח הפרויקט
            issue_type (str): סוג הIssue
            
        Returns:
            Dict: מידע על שדות הIssue כולל חובה/אופציונלי
        """
        metadata = self.get_create_issue_metadata(project_key, issue_type)
        
        if not metadata or 'projects' not in metadata:
            return {}
            
        try:
            project = metadata['projects'][0]
            for issuetype in project['issuetypes']:
                if issuetype['name'] == issue_type:
                    return issuetype['fields']
            return {}
        except (IndexError, KeyError) as e:
            print(f"שגיאה בעיבוד מטא-דאטה: {str(e)}")
            return {}

    def print_available_fields(self, project_key: str, issue_type: str = None):
        """
        הדפסת רשימת השדות הזמינים בפורמט ברור
        
        Args:
            project_key (str): מפתח הפרויקט
            issue_type (str): סוג הIssue (אופציונלי)
        """
        if issue_type:
            fields = self.get_fields_for_issue_type(project_key, issue_type)
            if fields:
                print(f"\n🔍 שדות זמינים עבור {issue_type} בפרויקט {project_key}:")
                print("=" * 60)
                
                required_fields = []
                optional_fields = []
                
                for field_id, field_info in fields.items():
                    field_name = field_info.get('name', field_id)
                    field_type = field_info.get('schema', {}).get('type', 'unknown')
                    is_required = field_info.get('required', False)
                    
                    field_desc = f"🔹 {field_name} ({field_id}) - סוג: {field_type}"
                    
                    if 'allowedValues' in field_info and field_info['allowedValues']:
                        values = [v.get('name', v.get('value', str(v))) for v in field_info['allowedValues']]
                        field_desc += f" - ערכים: {', '.join(values[:5])}"
                        if len(values) > 5:
                            field_desc += f" ועוד {len(values) - 5}..."
                    
                    if is_required:
                        required_fields.append(field_desc)
                    else:
                        optional_fields.append(field_desc)
                
                if required_fields:
                    print("\n🚨 שדות חובה:")
                    for field in required_fields:
                        print(f"  {field}")
                
                if optional_fields:
                    print("\n✨ שדות אופציונליים:")
                    for field in optional_fields:
                        print(f"  {field}")
            else:
                print(f"לא נמצאו שדות עבור {issue_type} בפרויקט {project_key}")
        else:
            metadata = self.get_create_issue_metadata(project_key)
            if metadata and 'projects' in metadata:
                project = metadata['projects'][0]
                print(f"\n🔍 סוגי Issues זמינים בפרויקט {project_key}:")
                print("=" * 50)
                
                for issuetype in project['issuetypes']:
                    print(f"🔸 {issuetype['name']} - {issuetype.get('description', 'ללא תיאור')}")
                
                print(f"\n💡 השתמש ב-print_available_fields('{project_key}', 'סוג_Issue') לראות שדות ספציפיים")

    def get_field_suggestions(self, project_key: str, issue_type: str) -> Dict:
        """
        קבלת הצעות לערכים בשדות (לדוגמה: רשימת משתמשים, components וכו')
        
        Args:
            project_key (str): מפתח הפרויקט
            issue_type (str): סוג הIssue
            
        Returns:
            Dict: הצעות לערכים בשדות שונים
        """
        suggestions = {}
        
        try:
            # קבלת משתמשים שניתן להקצות
            assignable_users = self.get_assignable_users(project_key)
            if assignable_users:
                suggestions['assignee'] = [
                    {
                        'name': user.get('name', user.get('accountId')),
                        'displayName': user.get('displayName'),
                        'emailAddress': user.get('emailAddress')
                    }
                    for user in assignable_users
                ]
            
            # קבלת components
            components = self.get_project_components(project_key)
            if components:
                suggestions['components'] = [
                    {'name': comp['name'], 'description': comp.get('description', '')}
                    for comp in components
                ]
            
            # קבלת versions
            versions = self.get_project_versions(project_key)
            if versions:
                suggestions['versions'] = [
                    {'name': ver['name'], 'released': ver.get('released', False)}
                    for ver in versions
                ]
            
            return suggestions
            
        except Exception as e:
            print(f"שגיאה בקבלת הצעות: {str(e)}")
            return {}

    def get_assignable_users(self, project_key: str) -> List[Dict]:
        """
        קבלת רשימת משתמשים שניתן להקצות בפרויקט
        """
        try:
            response = requests.get(
                f"{self.api_url}/user/assignable/search",
                headers=self.headers,
                params={'project': project_key}
            )
            
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"שגיאה בקבלת משתמשים: {str(e)}")
            return []

    def get_project_components(self, project_key: str) -> List[Dict]:
        """
        קבלת components של הפרויקט
        """
        try:
            response = requests.get(
                f"{self.api_url}/project/{project_key}/components",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"שגיאה בקבלת components: {str(e)}")
            return []

    def get_project_versions(self, project_key: str) -> List[Dict]:
        """
        קבלת versions של הפרויקט
        """
        try:
            response = requests.get(
                f"{self.api_url}/project/{project_key}/versions",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"שגיאה בקבלת versions: {str(e)}")
            return []
    
    def create_issue_interactive(self, project_key: str, issue_type: str = None) -> Optional[Dict]:
        """
        יצירת Issue בצורה אינטראקטיבית עם הנחיה לשדות
        
        Args:
            project_key (str): מפתח הפרויקט
            issue_type (str): סוג הIssue (אופציונלי)
            
        Returns:
            Optional[Dict]: מידע על הIssue שנוצר
        """
        if not issue_type:
            print("סוגי Issues זמינים:")
            self.print_available_fields(project_key)
            return None
            
        fields = self.get_fields_for_issue_type(project_key, issue_type)
        if not fields:
            print(f"לא נמצאו שדות עבור {issue_type}")
            return None
            
        print(f"\n🔧 יצירת Issue חדש מסוג {issue_type}")
        print("=" * 40)
        
        # בניית נתוני הIssue
        issue_fields = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type}
        }
        
        # השדות הבסיסיים הנדרשים
        for field_id, field_info in fields.items():
            if not field_info.get('required', False):
                continue
                
            field_name = field_info.get('name', field_id)
            field_type = field_info.get('schema', {}).get('type')
            
            # דילוג על שדות שכבר מוגדרים
            if field_id in ['project', 'issuetype']:
                continue
                
            print(f"\n📝 {field_name} (חובה):")
            
            if field_id == 'summary':
                value = input("  הזן כותרת: ")
                issue_fields['summary'] = value
                
            elif field_id == 'description':
                value = input("  הזן תיאור: ")
                if value:
                    issue_fields['description'] = {
                        "type": "doc",
                        "version": 1,
                        "content": [{
                            "type": "paragraph",
                            "content": [{
                                "type": "text",
                                "text": value
                            }]
                        }]
                    }
                    
            elif 'allowedValues' in field_info and field_info['allowedValues']:
                print("  ערכים זמינים:")
                for i, option in enumerate(field_info['allowedValues']):
                    name = option.get('name', option.get('value', str(option)))
                    print(f"    {i+1}. {name}")
                
                try:
                    choice = int(input("  בחר מספר: ")) - 1
                    if 0 <= choice < len(field_info['allowedValues']):
                        selected = field_info['allowedValues'][choice]
                        issue_fields[field_id] = {"id": selected['id']} if 'id' in selected else {"name": selected['name']}
                except ValueError:
                    print("  מספר לא תקין, מדלג על השדה")
                    
            else:
                value = input(f"  הזן ערך עבור {field_name}: ")
                if value:
                    issue_fields[field_id] = value
        
        # יצירת הIssue
        try:
            response = requests.post(
                f"{self.api_url}/issue",
                headers=self.headers,
                data=json.dumps({"fields": issue_fields})
            )
            
            if response.status_code == 201:
                created_issue = response.json()
                print(f"\n✅ Issue נוצר בהצלחה: {created_issue['key']}")
                return created_issue
            else:
                print(f"\n❌ שגיאה ביצירת Issue: {response.status_code}")
                print(f"פרטים: {response.text}")
                return None
                
        except Exception as e:
            print(f"שגיאה ביצירת Issue: {str(e)}")
            return None

    def validate_field_value(self, project_key: str, issue_type: str, field_id: str, value: Any) -> bool:
        """
        בדיקת תקינות ערך שדה לפני יצירת Issue
        
        Args:
            project_key (str): מפתח הפרויקט
            issue_type (str): סוג הIssue
            field_id (str): מזהה השדה
            value (Any): הערך לבדיקה
            
        Returns:
            bool: True אם הערך תקין, False אחרת
        """
        fields = self.get_fields_for_issue_type(project_key, issue_type)
        
        if field_id not in fields:
            print(f"שדה {field_id} לא קיים")
            return False
            
        field_info = fields[field_id]
        
        # בדיקה אם השדה חובה וריק
        if field_info.get('required', False) and not value:
            print(f"שדה {field_info.get('name', field_id)} הוא חובה")
            return False
            
        # בדיקה אם הערך מתוך הרשימה המותרת
        if 'allowedValues' in field_info and field_info['allowedValues']:
            allowed_names = [v.get('name', v.get('value', str(v))) for v in field_info['allowedValues']]
            if isinstance(value, dict) and 'name' in value:
                if value['name'] not in allowed_names:
                    print(f"ערך {value['name']} לא מותר עבור {field_info.get('name', field_id)}")
                    print(f"ערכים מותרים: {', '.join(allowed_names)}")
                    return False
            elif isinstance(value, str) and value not in allowed_names:
                print(f"ערך {value} לא מותר עבור {field_info.get('name', field_id)}")
                print(f"ערכים מותרים: {', '.join(allowed_names)}")
                return False
                
        return True
                    issue_type: str = "Task", priority: str = "Medium",
                    assignee: str = None, labels: List[str] = None,
                    custom_fields: Dict[str, Any] = None) -> Optional[Dict]:
        """
        יצירת Issue חדש
        
        Args:
            project_key (str): מפתח הפרויקט
            summary (str): כותרת הIssue
            description (str): תיאור הIssue
            issue_type (str): סוג הIssue (Task, Bug, Story וכו')
            priority (str): עדיפות (Highest, High, Medium, Low, Lowest)
            assignee (str): שם המשתמש למי להקצות
            labels (List[str]): תוויות
            custom_fields (Dict): שדות מותאמים אישית
            
        Returns:
            Optional[Dict]: מידע על הIssue שנוצר או None אם נכשל
        """
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": issue_type},
                "priority": {"name": priority}
            }
        }
        
        # הוספת assignee אם סופק
        if assignee:
            issue_data["fields"]["assignee"] = {"name": assignee}
        
        # הוספת labels אם סופקו
        if labels:
            issue_data["fields"]["labels"] = labels
        
        # הוספת שדות מותאמים אישית
        if custom_fields:
            issue_data["fields"].update(custom_fields)
        
        try:
            response = requests.post(
                f"{self.api_url}/issue",
                headers=self.headers,
                data=json.dumps(issue_data)
            )
            
            if response.status_code == 201:
                created_issue = response.json()
                print(f"Issue נוצר בהצלחה: {created_issue['key']}")
                return created_issue
            else:
                print(f"שגיאה ביצירת Issue: {response.status_code}")
                print(f"תגובה: {response.text}")
                return None
                
        except Exception as e:
            print(f"שגיאה ביצירת Issue: {str(e)}")
            return None
    
    def get_issue(self, issue_key: str) -> Optional[Dict]:
        """
        קבלת מידע על Issue ספציפי
        
        Args:
            issue_key (str): מפתח הIssue
            
        Returns:
            Optional[Dict]: מידע על הIssue או None אם לא נמצא
        """
        try:
            response = requests.get(
                f"{self.api_url}/issue/{issue_key}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"שגיאה בקבלת Issue: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"שגיאה: {str(e)}")
            return None
    
    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> bool:
        """
        עדכון Issue קיים
        
        Args:
            issue_key (str): מפתח הIssue
            fields (Dict): השדות לעדכון
            
        Returns:
            bool: True אם העדכון הצליח, False אחרת
        """
        update_data = {"fields": fields}
        
        try:
            response = requests.put(
                f"{self.api_url}/issue/{issue_key}",
                headers=self.headers,
                data=json.dumps(update_data)
            )
            
            if response.status_code == 204:
                print(f"Issue {issue_key} עודכן בהצלחה")
                return True
            else:
                print(f"שגיאה בעדכון Issue: {response.status_code}")
                print(f"תגובה: {response.text}")
                return False
                
        except Exception as e:
            print(f"שגיאה בעדכון Issue: {str(e)}")
            return False
    
    def delete_issue(self, issue_key: str) -> bool:
        """
        מחיקת Issue
        
        Args:
            issue_key (str): מפתח הIssue
            
        Returns:
            bool: True אם המחיקה הצליחה, False אחרת
        """
        try:
            response = requests.delete(
                f"{self.api_url}/issue/{issue_key}",
                headers=self.headers
            )
            
            if response.status_code == 204:
                print(f"Issue {issue_key} נמחק בהצלחה")
                return True
            else:
                print(f"שגיאה במחיקת Issue: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"שגיאה במחיקת Issue: {str(e)}")
            return False
    
    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict]:
        """
        חיפוש Issues באמצעות JQL
        
        Args:
            jql (str): שאילתת JQL
            max_results (int): מספר התוצאות המקסימלי
            
        Returns:
            List[Dict]: רשימת Issues שנמצאו
        """
        search_data = {
            "jql": jql,
            "maxResults": max_results
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/search",
                headers=self.headers,
                data=json.dumps(search_data)
            )
            
            if response.status_code == 200:
                return response.json().get("issues", [])
            else:
                print(f"שגיאה בחיפוש: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"שגיאה בחיפוש: {str(e)}")
            return []
    
    def add_comment(self, issue_key: str, comment: str) -> bool:
        """
        הוספת תגובה לIssue
        
        Args:
            issue_key (str): מפתח הIssue
            comment (str): התגובה
            
        Returns:
            bool: True אם התגובה נוספה בהצלחה, False אחרת
        """
        comment_data = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/issue/{issue_key}/comment",
                headers=self.headers,
                data=json.dumps(comment_data)
            )
            
            if response.status_code == 201:
                print(f"תגובה נוספה בהצלחה לIssue {issue_key}")
                return True
            else:
                print(f"שגיאה בהוספת תגובה: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"שגיאה בהוספת תגובה: {str(e)}")
            return False
    
    def get_issue_transitions(self, issue_key: str) -> List[Dict]:
        """
        קבלת מעברי סטטוס זמינים לIssue
        
        Args:
            issue_key (str): מפתח הIssue
            
        Returns:
            List[Dict]: רשימת מעברי סטטוס זמינים
        """
        try:
            response = requests.get(
                f"{self.api_url}/issue/{issue_key}/transitions",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json().get("transitions", [])
            else:
                print(f"שגיאה בקבלת מעברי סטטוס: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"שגיאה: {str(e)}")
            return []
    
    def transition_issue(self, issue_key: str, transition_id: str) -> bool:
        """
        ביצוע מעבר סטטוס לIssue
        
        Args:
            issue_key (str): מפתח הIssue
            transition_id (str): מזהה המעבר
            
        Returns:
            bool: True אם המעבר הצליח, False אחרת
        """
        transition_data = {
            "transition": {
                "id": transition_id
            }
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/issue/{issue_key}/transitions",
                headers=self.headers,
                data=json.dumps(transition_data)
            )
            
            if response.status_code == 204:
                print(f"מעבר סטטוס בוצע בהצלחה עבור Issue {issue_key}")
                return True
            else:
                print(f"שגיאה במעבר סטטוס: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"שגיאה במעבר סטטוס: {str(e)}")
            return False


# דוגמא לשימוש
if __name__ == "__main__":
    # יצירת מופע של המחלקה
    jira = JiraIssueManager(
        base_url="https://your-domain.atlassian.net",
        username="your-email@example.com",
        token="your-api-token"
    )
    
    # בדיקת חיבור
    if jira.test_connection():
        # יצירת Issue חדש
        new_issue = jira.create_issue(
            project_key="PROJ",
            summary="Issue חדש מהקוד",
            description="זהו תיאור של הIssue החדש",
            issue_type="Task",
            priority="High",
            labels=["api", "python"]
        )
        
        if new_issue:
            issue_key = new_issue["key"]
            print(f"נוצר Issue: {issue_key}")
            
            # הוספת תגובה
            jira.add_comment(issue_key, "תגובה מהקוד")
            
            # קבלת מידע על הIssue
            issue_info = jira.get_issue(issue_key)
            if issue_info:
                print(f"כותרת: {issue_info['fields']['summary']}")
                print(f"סטטוס: {issue_info['fields']['status']['name']}")
    
    # חיפוש Issues
    results = jira.search_issues("project = PROJ AND status = 'To Do'")
    print(f"נמצאו {len(results)} Issues")
