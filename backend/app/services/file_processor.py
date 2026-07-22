"""
File processor for data ingestion from Excel, CSV, PDF, and Primavera files
"""
from typing import Dict, Any, List
from pathlib import Path
import pandas as pd
from datetime import datetime
from app.core.logging import get_logger

logger = get_logger(__name__)


class FileProcessor:
    """Process uploaded files and extract project data"""
    
    def __init__(self):
        self.supported_formats = {
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.csv': 'csv',
            '.pdf': 'pdf',
            '.mpp': 'ms_project',
            '.xml': 'primavera'
        }
    
    async def process_file(self, file_path: str, project_id: str, file_type: str) -> Dict[str, Any]:
        """Process uploaded file based on its type"""
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension not in self.supported_formats:
                return {
                    "success": False,
                    "error": f"Unsupported file format: {file_extension}"
                }
            
            processor_type = self.supported_formats[file_extension]
            
            if processor_type == 'excel':
                return await self.process_excel(file_path, project_id)
            elif processor_type == 'csv':
                return await self.process_csv(file_path, project_id)
            elif processor_type == 'pdf':
                return await self.process_pdf(file_path, project_id)
            elif processor_type == 'primavera':
                return await self.process_primavera(file_path, project_id)
            elif processor_type == 'ms_project':
                return await self.process_ms_project(file_path, project_id)
            else:
                return {
                    "success": False,
                    "error": f"Processor not implemented for: {processor_type}"
                }
        
        except Exception as e:
            logger.error(f"File processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_excel(self, file_path: str, project_id: str) -> Dict[str, Any]:
        """Process Excel file and extract schedule/procurement data"""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            extracted_data = {
                "success": True,
                "file_type": "excel",
                "project_id": project_id,
                "sheets": [],
                "activities": [],
                "resources": [],
                "procurement": []
            }
            
            # Process each sheet
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                sheet_data = {
                    "name": sheet_name,
                    "rows": len(df),
                    "columns": list(df.columns)
                }
                
                # Detect sheet type based on columns
                if self._is_activity_sheet(df):
                    activities = self._extract_activities(df)
                    extracted_data["activities"].extend(activities)
                    sheet_data["type"] = "activities"
                elif self._is_procurement_sheet(df):
                    procurement = self._extract_procurement(df)
                    extracted_data["procurement"].extend(procurement)
                    sheet_data["type"] = "procurement"
                elif self._is_resource_sheet(df):
                    resources = self._extract_resources(df)
                    extracted_data["resources"].extend(resources)
                    sheet_data["type"] = "resources"
                else:
                    sheet_data["type"] = "unknown"
                
                extracted_data["sheets"].append(sheet_data)
            
            logger.info(f"Excel file processed: {len(extracted_data['activities'])} activities, {len(extracted_data['procurement'])} procurement items")
            
            return extracted_data
        
        except Exception as e:
            logger.error(f"Excel processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Excel processing failed: {str(e)}"
            }
    
    async def process_csv(self, file_path: str, project_id: str) -> Dict[str, Any]:
        """Process CSV file and extract data"""
        try:
            df = pd.read_csv(file_path)
            
            extracted_data = {
                "success": True,
                "file_type": "csv",
                "project_id": project_id,
                "rows": len(df),
                "columns": list(df.columns),
                "activities": [],
                "procurement": []
            }
            
            # Detect data type
            if self._is_activity_sheet(df):
                extracted_data["activities"] = self._extract_activities(df)
            elif self._is_procurement_sheet(df):
                extracted_data["procurement"] = self._extract_procurement(df)
            
            logger.info(f"CSV file processed: {len(extracted_data['activities'])} activities")
            
            return extracted_data
        
        except Exception as e:
            logger.error(f"CSV processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"CSV processing failed: {str(e)}"
            }
    
    async def process_pdf(self, file_path: str, project_id: str) -> Dict[str, Any]:
        """Process PDF file and extract text data"""
        try:
            import PyPDF2
            
            extracted_data = {
                "success": True,
                "file_type": "pdf",
                "project_id": project_id,
                "text_content": "",
                "pages": 0
            }
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                extracted_data["pages"] = len(pdf_reader.pages)
                
                text_content = []
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
                
                extracted_data["text_content"] = "\n".join(text_content)
            
            logger.info(f"PDF file processed: {extracted_data['pages']} pages")
            
            return extracted_data
        
        except Exception as e:
            logger.error(f"PDF processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"PDF processing failed: {str(e)}"
            }
    
    async def process_primavera(self, file_path: str, project_id: str) -> Dict[str, Any]:
        """Process Primavera XML export file"""
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            extracted_data = {
                "success": True,
                "file_type": "primavera",
                "project_id": project_id,
                "activities": [],
                "resources": [],
                "relationships": []
            }
            
            # Extract activities
            for activity in root.findall('.//Activity'):
                activity_data = {
                    "activity_id": activity.get('ActivityID'),
                    "activity_name": activity.get('Name'),
                    "activity_type": activity.get('Type'),
                    "duration": activity.get('Duration'),
                    "start_date": activity.get('StartDate'),
                    "finish_date": activity.get('FinishDate'),
                    "percent_complete": activity.get('PercentComplete', 0)
                }
                extracted_data["activities"].append(activity_data)
            
            # Extract relationships (dependencies)
            for relationship in root.findall('.//Relationship'):
                rel_data = {
                    "predecessor_id": relationship.get('PredecessorID'),
                    "successor_id": relationship.get('SuccessorID'),
                    "relationship_type": relationship.get('Type'),
                    "lag": relationship.get('Lag', 0)
                }
                extracted_data["relationships"].append(rel_data)
            
            logger.info(f"Primavera file processed: {len(extracted_data['activities'])} activities")
            
            return extracted_data
        
        except Exception as e:
            logger.error(f"Primavera processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Primavera processing failed: {str(e)}"
            }
    
    async def process_ms_project(self, file_path: str, project_id: str) -> Dict[str, Any]:
        """Process MS Project file"""
        try:
            # MS Project files require specialized libraries
            # This is a placeholder for future implementation
            extracted_data = {
                "success": True,
                "file_type": "ms_project",
                "project_id": project_id,
                "message": "MS Project processing requires additional library implementation",
                "activities": []
            }
            
            logger.warning("MS Project processing not fully implemented")
            
            return extracted_data
        
        except Exception as e:
            logger.error(f"MS Project processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"MS Project processing failed: {str(e)}"
            }
    
    def _is_activity_sheet(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame contains activity data"""
        activity_keywords = ['activity', 'task', 'id', 'name', 'start', 'finish', 'duration']
        columns_lower = [col.lower() for col in df.columns]
        return any(keyword in ' '.join(columns_lower) for keyword in activity_keywords)
    
    def _is_procurement_sheet(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame contains procurement data"""
        procurement_keywords = ['po', 'purchase', 'order', 'supplier', 'material', 'item', 'quantity']
        columns_lower = [col.lower() for col in df.columns]
        return any(keyword in ' '.join(columns_lower) for keyword in procurement_keywords)
    
    def _is_resource_sheet(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame contains resource data"""
        resource_keywords = ['resource', 'labor', 'equipment', 'cost', 'rate']
        columns_lower = [col.lower() for col in df.columns]
        return any(keyword in ' '.join(columns_lower) for keyword in resource_keywords)
    
    def _extract_activities(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract activity data from DataFrame"""
        activities = []
        
        # Map common column names to standard names
        column_mapping = {
            'activity id': 'activity_id',
            'activity_id': 'activity_id',
            'id': 'activity_id',
            'activity name': 'activity_name',
            'activity_name': 'activity_name',
            'name': 'activity_name',
            'task name': 'activity_name',
            'start': 'start_date',
            'start_date': 'start_date',
            'finish': 'finish_date',
            'finish_date': 'finish_date',
            'end_date': 'finish_date',
            'duration': 'duration',
            'original_duration': 'duration',
            'percent complete': 'percent_complete',
            'percent_complete': 'percent_complete',
            'progress': 'percent_complete'
        }
        
        # Rename columns
        df.columns = [column_mapping.get(col.lower(), col.lower()) for col in df.columns]
        
        for _, row in df.iterrows():
            activity = {
                "activity_id": str(row.get('activity_id', '')),
                "activity_name": str(row.get('activity_name', '')),
                "start_date": self._parse_date(row.get('start_date')),
                "finish_date": self._parse_date(row.get('finish_date')),
                "duration": self._parse_number(row.get('duration')),
                "percent_complete": self._parse_number(row.get('percent_complete', 0))
            }
            
            if activity['activity_id']:  # Only add if has ID
                activities.append(activity)
        
        return activities
    
    def _extract_procurement(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract procurement data from DataFrame"""
        procurement_items = []
        
        column_mapping = {
            'po number': 'po_number',
            'po_number': 'po_number',
            'purchase order': 'po_number',
            'supplier': 'supplier_name',
            'supplier_name': 'supplier_name',
            'material': 'material_name',
            'material_name': 'material_name',
            'item': 'material_name',
            'description': 'description',
            'quantity': 'quantity',
            'qty': 'quantity',
            'unit': 'unit',
            'unit_price': 'unit_price',
            'price': 'unit_price',
            'total': 'total_price'
        }
        
        # Rename columns
        df.columns = [column_mapping.get(col.lower(), col.lower()) for col in df.columns]
        
        for _, row in df.iterrows():
            item = {
                "po_number": str(row.get('po_number', '')),
                "supplier_name": str(row.get('supplier_name', '')),
                "material_name": str(row.get('material_name', '')),
                "description": str(row.get('description', '')),
                "quantity": self._parse_number(row.get('quantity')),
                "unit": str(row.get('unit', '')),
                "unit_price": self._parse_number(row.get('unit_price')),
                "total_price": self._parse_number(row.get('total_price'))
            }
            
            if item['po_number'] or item['material_name']:
                procurement_items.append(item)
        
        return procurement_items
    
    def _extract_resources(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract resource data from DataFrame"""
        resources = []
        
        column_mapping = {
            'resource id': 'resource_id',
            'resource_id': 'resource_id',
            'resource name': 'resource_name',
            'resource_name': 'resource_name',
            'name': 'resource_name',
            'type': 'resource_type',
            'resource_type': 'resource_type',
            'cost': 'cost_per_unit',
            'cost_per_unit': 'cost_per_unit',
            'rate': 'cost_per_unit'
        }
        
        # Rename columns
        df.columns = [column_mapping.get(col.lower(), col.lower()) for col in df.columns]
        
        for _, row in df.iterrows():
            resource = {
                "resource_id": str(row.get('resource_id', '')),
                "resource_name": str(row.get('resource_name', '')),
                "resource_type": str(row.get('resource_type', '')),
                "cost_per_unit": self._parse_number(row.get('cost_per_unit'))
            }
            
            if resource['resource_name']:
                resources.append(resource)
        
        return resources
    
    def _parse_date(self, date_value) -> str:
        """Parse date value and return ISO format string"""
        if pd.isna(date_value):
            return None
        
        if isinstance(date_value, str):
            try:
                parsed_date = pd.to_datetime(date_value)
                return parsed_date.isoformat()
            except:
                return date_value
        
        if isinstance(date_value, (pd.Timestamp, datetime)):
            return date_value.isoformat()
        
        return str(date_value)
    
    def _parse_number(self, number_value) -> float:
        """Parse number value"""
        if pd.isna(number_value):
            return 0.0
        
        try:
            return float(number_value)
        except (ValueError, TypeError):
            return 0.0
