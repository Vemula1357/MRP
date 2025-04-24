import os
import json
import pandas as pd

json_folder = "fhir"
output_excel = "patient_data.xlsx"

patients, symptoms, diagnoses, treatments = [], [], [], []

for filename in os.listdir(json_folder):
    if filename.endswith(".json"):
        with open(os.path.join(json_folder, filename), "r", encoding="utf-8") as file:
            content = file.read().strip() 
            if not content:  
                print(f"Skipping empty file: {filename}")
                continue
            
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in file: {filename}")
                print(f"Error details: {e}")
                continue  


            for entry in json_data.get("entry", []): 
                resource = entry.get("resource", {})

                if resource.get("resourceType") == "Patient":
                    patients.append({
                        "Patient ID": resource.get("id", ""),
                        "Name": f"{resource.get('name', [{}])[0].get('given', [''])[0]} {resource.get('name', [{}])[0].get('family', '')}",
                        "Gender": resource.get("gender", ""),
                        "Birth Date": resource.get("birthDate", ""),
                        "Phone": resource.get("telecom", [{}])[0].get("value", "")
                    })
                
                elif resource.get("resourceType") == "Observation":
                    symptoms.append({
                        "Patient ID": resource.get("subject", {}).get("reference", "").split(":")[-1],
                        "Symptom": resource.get("code", {}).get("text", "Unknown"),
                        "Recorded Date": resource.get("effectiveDateTime", "Unknown")
                    })
                
                elif resource.get("resourceType") == "Condition":
                    diagnoses.append({
                        "Patient ID": resource.get("subject", {}).get("reference", "").split(":")[-1],
                        "Diagnosis": resource.get("code", {}).get("text", "Unknown"),
                        "Onset Date": resource.get("onsetDateTime", "Unknown")
                    })
                
                elif resource.get("resourceType") == "MedicationRequest":
                    treatments.append({
                        "Patient ID": resource.get("subject", {}).get("reference", "").split(":")[-1],
                        "Medication": resource.get("medicationCodeableConcept", {}).get("text", "Unknown"),
                        "Prescribed By": resource.get("requester", {}).get("display", "Unknown"),
                        "Date": resource.get("authoredOn", "Unknown")
                    })

with pd.ExcelWriter(output_excel) as writer:
    pd.DataFrame(patients).to_excel(writer, sheet_name="Patients", index=False)
    pd.DataFrame(symptoms).to_excel(writer, sheet_name="Symptoms", index=False)
    pd.DataFrame(diagnoses).to_excel(writer, sheet_name="Diagnoses", index=False)
    pd.DataFrame(treatments).to_excel(writer, sheet_name="Treatments", index=False)

print(f"✅ Excel file saved successfully at: {output_excel}")
