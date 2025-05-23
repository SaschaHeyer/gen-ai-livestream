import requests
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import base64
import os
from IPython.display import display, HTML
from google import genai
from google.genai import types
from tqdm import tqdm
import sys
import json
import csv
import pandas as pd

class LinkedInSearchApp:
    def __init__(self, serpapi_key="", google_project="sascha-playground-doit"):
        self.serpapi_key = serpapi_key
        self.google_project = google_project
        self.names = [
            "Sascha Heyer",
        ]
        self.total_cost = 0.0
        self.cost_breakdown = []
        self.progress_file = "linkedin_processing_progress.txt"

    def search_linkedin_profiles(self):
        """Search for LinkedIn profiles using SerpAPI"""
        print("\n🔍 SEARCHING FOR LINKEDIN PROFILES")
        print("=" * 50)
        results = []

        for name in tqdm(self.names, desc="Searching profiles", ncols=70):
            query = f'site:linkedin.com/in/ "{name}"'
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.serpapi_key
            }
            try:
                print(f"  🔎 Searching for: {name.title()}")
                response = requests.get("https://serpapi.com/search", params=params)
                data = response.json()
                link = data.get("organic_results", [{}])[0].get("link", "Not found")
                if link.startswith("http"):
                    print(f"  ✅ Found: {link[:50]}...")
                else:
                    print(f"  ❌ Not found: {link}")
            except Exception as e:
                link = f"Error: {e}"
                print(f"  ⚠️  Error: {e}")
            results.append((name.title(), link))
            time.sleep(0.5)  # Small delay to avoid rate limiting

        print(f"\n✅ Search complete! Found {len([r for r in results if r[1].startswith('http')])} valid profiles\n")
        return results

    def display_search_results(self, results):
        """Display search results in HTML table format"""
        html = "<table><tr><th>Name</th><th>LinkedIn</th></tr>"
        for name, link in results:
            if link.startswith("http"):
                html += f'<tr><td>{name}</td><td><a href="{link}" target="_blank">{link}</a></td></tr>'
            else:
                html += f'<tr><td>{name}</td><td>{link}</td></tr>'
        html += "</table>"
        display(HTML(html))
        return results

    def take_linkedin_screenshot(self, profile_url, output_filename):
        """Take a full page screenshot of a LinkedIn profile"""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,3000")
        options.add_argument("--user-data-dir=/tmp/selenium")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")

        driver = webdriver.Chrome(options=options)

        try:
            driver.get("https://www.linkedin.com")

            # Load cookies if they exist
            if os.path.exists("linkedin_cookies.pkl"):
                cookies = pickle.load(open("linkedin_cookies.pkl", "rb"))
                for cookie in cookies:
                    driver.add_cookie(cookie)

            driver.get(profile_url)

            # Wait for profile content to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "artdeco-card"))
                )
                time.sleep(2)
            except:
                pass

            # Scroll to the bottom of the page to load all content
            last_height = driver.execute_script("return document.body.scrollHeight")

            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # Resize window to full page height for screenshot
            S = lambda X: driver.execute_script(f'return document.body.parentNode.scroll{X}')
            driver.set_window_size(S('Width'), S('Height'))
            time.sleep(2)
            driver.save_screenshot(output_filename)

        finally:
            driver.quit()

        return output_filename

    def extract_entities_from_screenshot(self, screenshot_path):
        """Extract job title and company from LinkedIn screenshot using Gemini with structured JSON output"""
        start_time = time.time()

        client = genai.Client(
            vertexai=True,
            project=self.google_project,
            location="global",
        )

        # Read and encode the screenshot
        with open(screenshot_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode()

        msg1_image1 = types.Part.from_bytes(
            data=base64.b64decode(image_data),
            mime_type="image/png",
        )

        model = "gemini-2.0-flash-001"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text="extract entities from this linkedin screenshot"),
                    msg1_image1
                ]
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=1,
            max_output_tokens=8192,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
            ],
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "job_title": {"type": "STRING"},
                    "current_company": {"type": "STRING"}
                }
            },
            system_instruction=[types.Part.from_text(text="you are a entity extraction specialist extract the following entities\n\n- job title\n- current company")],
        )

        # Use non-streaming response for cost tracking
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)

        # Calculate cost based on token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count

        # Pricing for gemini-2.0-flash-001: Input $0.10/1M tokens, Output $0.40/1M tokens
        input_cost = (input_tokens / 1_000_000) * 0.10
        output_cost = (output_tokens / 1_000_000) * 0.40
        total_cost = input_cost + output_cost

        # Track costs
        self.total_cost += total_cost
        cost_info = {
            "operation": "entity_extraction",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.total_token_count,
            "cost_usd": round(total_cost, 6),
            "response_time_ms": response_time_ms
        }
        self.cost_breakdown.append(cost_info)

        try:
            # Parse the JSON response
            entities_json = json.loads(response.text)

            # Add cost info to response
            entities_json.update(cost_info)
            return entities_json
        except json.JSONDecodeError:
            fallback_result = {"job_title": "Unknown", "current_company": "Unknown", "raw_text": response.text}
            fallback_result.update(cost_info)
            return fallback_result

    def get_company_information(self, company_name):
        """Get comprehensive company information using two-step grounding + extraction process"""
        # Step 1: Grounding search for comprehensive company information
        grounding_data = self._perform_grounding_search(company_name)

        # Step 2: Extract structured data from grounding response
        structured_data = self._extract_structured_company_data(grounding_data["text"])

        # Combine cost information
        total_cost = grounding_data["cost_usd"] + structured_data["cost_usd"]
        combined_info = {
            **structured_data,
            "grounding_text": grounding_data["text"],
            "total_cost_usd": round(total_cost, 6),
            "grounding_cost_usd": grounding_data["cost_usd"],
            "extraction_cost_usd": structured_data["cost_usd"]
        }

        return combined_info

    def _perform_grounding_search(self, company_name):
        """Step 1: Perform grounding search to gather comprehensive company information"""
        start_time = time.time()

        client = genai.Client(
            vertexai=True,
            project=self.google_project,
            location="global",
        )

        model = "gemini-2.0-flash-001"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"""I need information for the following company: {company_name}

- how many employees work at {company_name}. only return a single number no additional text
- company headquarter city
- company headquarters country
- company website
- summary of the company""")
                ]
            ),
        ]

        tools = [
            types.Tool(google_search=types.GoogleSearch()),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=1,
            max_output_tokens=8192,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
            ],
            tools=tools,
        )

        # Use non-streaming response for cost tracking
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)

        # Calculate cost based on token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count

        # Pricing for gemini-2.0-flash-001: Input $0.10/1M tokens, Output $0.40/1M tokens
        input_cost = (input_tokens / 1_000_000) * 0.10
        output_cost = (output_tokens / 1_000_000) * 0.40
        total_cost = input_cost + output_cost

        # Track costs
        self.total_cost += total_cost
        cost_info = {
            "operation": "grounding_search",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.total_token_count,
            "cost_usd": round(total_cost, 6),
            "response_time_ms": response_time_ms
        }
        self.cost_breakdown.append(cost_info)

        return {
            "text": response.text,
            **cost_info
        }

    def _extract_structured_company_data(self, grounding_text):
        """Step 2: Extract structured data from grounding response text"""
        start_time = time.time()

        client = genai.Client(
            vertexai=True,
            project=self.google_project,
            location="global",
        )

        model = "gemini-2.0-flash-001"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"Extract structured information from the following company research text:\n\n{grounding_text}")
                ]
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=0,
            top_p=1,
            max_output_tokens=8192,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
            ],
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "employee_count": {"type": "STRING"},
                    "headquarters_city": {"type": "STRING"},
                    "headquarters_country": {"type": "STRING"},
                    "company_website": {"type": "STRING"},
                    "company_summary": {"type": "STRING"}
                }
            },
            system_instruction=[types.Part.from_text(text="You are a company information extraction specialist. Extract the following entities from the provided company research text:\n\n- employee_count: Number of employees (as string)\n- headquarters_city: City where company headquarters is located\n- headquarters_country: Country where company headquarters is located  \n- company_website: Official company website URL\n- company_summary: Brief summary of what the company does\n\nIf information is not available, use 'Unknown' as the value.")],
        )

        # Use non-streaming response for cost tracking
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)

        # Calculate cost based on token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count

        # Pricing for gemini-2.0-flash-001: Input $0.10/1M tokens, Output $0.40/1M tokens
        input_cost = (input_tokens / 1_000_000) * 0.10
        output_cost = (output_tokens / 1_000_000) * 0.40
        total_cost = input_cost + output_cost

        # Track costs
        self.total_cost += total_cost
        cost_info = {
            "operation": "company_extraction",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.total_token_count,
            "cost_usd": round(total_cost, 6),
            "response_time_ms": response_time_ms
        }
        self.cost_breakdown.append(cost_info)

        try:
            # Parse the JSON response
            structured_json = json.loads(response.text)

            # Add cost info to response
            structured_json.update(cost_info)
            return structured_json
        except json.JSONDecodeError:
            fallback_result = {
                "employee_count": "Unknown",
                "headquarters_city": "Unknown",
                "headquarters_country": "Unknown",
                "company_website": "Unknown",
                "company_summary": "Unknown",
                "raw_text": response.text
            }
            fallback_result.update(cost_info)
            return fallback_result

    def save_results_to_csv(self, results, filename="linkedin_analysis_results.csv"):
        """Save analysis results to CSV file"""
        # Prepare data for CSV
        csv_data = []
        for result in results:
            entities = result.get('entities', {})
            company_info = result.get('company_info', {})
            row = {
                'name': result['name'],
                'job_title': result['job_title'],
                'company': result['company'],
                'employee_count': result['employee_count'],
                'headquarters_city': result.get('headquarters_city', 'Unknown'),
                'headquarters_country': result.get('headquarters_country', 'Unknown'),
                'company_website': result.get('company_website', 'Unknown'),
                'company_summary': result.get('company_summary', 'Unknown'),
                'linkedin_url': result['linkedin_url']
            }
            csv_data.append(row)

        # Write to CSV
        df = pd.DataFrame(csv_data)
        df.to_csv(filename, index=False)

        return filename

    def save_cost_breakdown_to_csv(self, filename="linkedin_analysis_costs.csv"):
        """Save detailed cost breakdown to CSV file"""
        if not self.cost_breakdown:
            return None

        # Add timestamp to each cost entry
        for entry in self.cost_breakdown:
            entry['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')

        # Write to CSV
        df = pd.DataFrame(self.cost_breakdown)
        df.to_csv(filename, index=False)

        return filename

    def load_processed_names(self):
        """Load list of already processed names from progress file"""
        if not os.path.exists(self.progress_file):
            return set()

        try:
            with open(self.progress_file, 'r') as f:
                processed = set(line.strip() for line in f if line.strip())
            return processed
        except Exception as e:
            print(f"⚠️ Error reading progress file: {e}")
            return set()

    def mark_as_processed(self, name):
        """Mark a person as processed in the progress file"""
        try:
            with open(self.progress_file, 'a') as f:
                f.write(f"{name}\n")
        except Exception as e:
            print(f"⚠️ Error updating progress file: {e}")

    def get_remaining_names(self):
        """Get list of names that haven't been processed yet"""
        processed = self.load_processed_names()
        remaining = [name for name in self.names if name not in processed]
        return remaining, processed

    def process_person(self, name, linkedin_url):
        """Process a single person: screenshot, extract entities, get company info"""
        if not linkedin_url.startswith("http"):
            return None

        try:
            # Take screenshot
            screenshot_filename = f"{name.lower().replace(' ', '_')}_profile.png"
            screenshot_path = self.take_linkedin_screenshot(linkedin_url, screenshot_filename)

            # Extract entities (now returns structured JSON)
            entities = self.extract_entities_from_screenshot(screenshot_path)

            # Get company name from structured response
            company_name = entities.get('current_company', 'Unknown Company')
            job_title = entities.get('job_title', 'Unknown Position')

            # Get comprehensive company information using two-step process
            company_info = self.get_company_information(company_name)

            return {
                "name": name,
                "linkedin_url": linkedin_url,
                "screenshot": screenshot_path,
                "job_title": job_title,
                "company": company_name,
                "employee_count": company_info.get('employee_count', 'Unknown'),
                "headquarters_city": company_info.get('headquarters_city', 'Unknown'),
                "headquarters_country": company_info.get('headquarters_country', 'Unknown'),
                "company_website": company_info.get('company_website', 'Unknown'),
                "company_summary": company_info.get('company_summary', 'Unknown'),
                "entities": entities,
                "company_info": company_info
            }

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None

    def run_full_analysis(self):
        """Run the complete analysis pipeline with incremental processing and CSV saving"""
        print("\n🚀 LINKEDIN SEARCH APPLICATION STARTED")
        print("=" * 60)

        # Check for existing progress
        remaining_names, processed_names = self.get_remaining_names()

        if processed_names:
            print(f"📂 Found existing progress: {len(processed_names)} people already processed")
            print(f"▶️  Resuming with {len(remaining_names)} remaining people")
        else:
            print(f"📋 Starting fresh: {len(self.names)} people to process")

        print(f"🔑 API Key: {self.serpapi_key[:10]}...")
        print(f"☁️  Google Project: {self.google_project}")

        # Load existing results from CSV if it exists
        all_results = self.load_existing_results()

        if not remaining_names:
            print("\n🎉 All people have already been processed!")
            return all_results

        # Process each remaining person individually: search -> process -> save -> mark as done
        total_people = len(self.names)
        start_index = total_people - len(remaining_names)

        for i, name in enumerate(remaining_names, start_index + 1):
            print(f"\n📍 Progress: {i}/{total_people} - {name}")

            try:
                # Step 1: Search for this person's LinkedIn profile
                linkedin_url = self._search_single_person(name)

                if not linkedin_url or not linkedin_url.startswith('http'):
                    print(f"❌ No valid LinkedIn profile found for {name}")
                    # Add person with "not found" status
                    result = {
                        "name": name,
                        "job_title": "Profile not found",
                        "company": "Profile not found",
                        "employee_count": "Profile not found",
                        "headquarters_city": "Profile not found",
                        "headquarters_country": "Profile not found",
                        "company_website": "Profile not found",
                        "company_summary": "Profile not found",
                        "linkedin_url": "Profile not found"
                    }
                    all_results.append(result)
                else:
                    # Step 2: Process this person completely
                    result = self.process_person(name, linkedin_url)

                    if result:
                        all_results.append(result)

                # Step 3: Save current results to CSV after each processing
                self.save_results_to_csv(all_results, "linkedin_analysis_results.csv")

                # Step 4: Mark as processed in progress file
                self.mark_as_processed(name)
                print(f"✅ {name} processed and saved ({len(all_results)} total profiles)")

            except Exception as e:
                print(f"❌ Error processing {name}: {str(e)}")
                # Add person with error status
                result = {
                    "name": name,
                    "job_title": "Processing error",
                    "company": "Processing error",
                    "employee_count": "Processing error",
                    "headquarters_city": "Processing error",
                    "headquarters_country": "Processing error",
                    "company_website": "Processing error",
                    "company_summary": "Processing error",
                    "linkedin_url": "Processing error"
                }
                all_results.append(result)
                self.save_results_to_csv(all_results, "linkedin_analysis_results.csv")
                self.mark_as_processed(name)
                print(f"⚠️ {name} marked as error and saved ({len(all_results)} total profiles)")
                continue

        return all_results

    def load_existing_results(self):
        """Load existing results from CSV if it exists"""
        try:
            if os.path.exists("linkedin_analysis_results.csv"):
                df = pd.read_csv("linkedin_analysis_results.csv")
                print(f"📊 Loaded {len(df)} existing results from CSV")
                return df.to_dict('records')
            else:
                return []
        except Exception as e:
            print(f"⚠️ Error loading existing CSV: {e}")
            return []

    def _search_single_person(self, name):
        """Search for a single person's LinkedIn profile"""
        query = f'site:linkedin.com/in/ "{name}"'
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.serpapi_key
        }

        try:
            response = requests.get("https://serpapi.com/search", params=params)
            data = response.json()
            link = data.get("organic_results", [{}])[0].get("link", "Not found")
            return link
        except Exception as e:
            print(f"Search error for {name}: {e}")
            return "Not found"

def main():
    # Initialize the app
    app = LinkedInSearchApp(
        serpapi_key="",
        google_project="sascha-playground-doit"
    )

    try:
        # Run the full analysis
        results = app.run_full_analysis()

        # Save results to CSV
        if results:
            app.save_results_to_csv(results)
            app.save_cost_breakdown_to_csv()

        # Display final results
        print("\n" + "🎉 " + "="*50 + " 🎉")
        print("           FINAL ANALYSIS RESULTS")
        print("🎉 " + "="*50 + " 🎉")

        if not results:
            print("❌ No results to display")
            return

        for i, result in enumerate(results, 1):
            print(f"\n👤 PERSON {i}: {result['name'].upper()}")
            print("-" * 40)
            print(f"💼 Job Title: {result['job_title']}")
            print(f"🏢 Company: {result['company']}")
            print(f"👥 Employee Count: {result['employee_count']}")
            print(f"🏙️  Headquarters: {result.get('headquarters_city', 'Unknown')}, {result.get('headquarters_country', 'Unknown')}")
            print(f"🌐 Website: {result.get('company_website', 'Unknown')}")
            print(f"📝 Summary: {result.get('company_summary', 'Unknown')[:100]}...")
            if result.get('screenshot') and result['screenshot'] != 'Profile not found':
                print(f"📸 Screenshot: {result['screenshot']}")
            print(f"🔗 LinkedIn: {result['linkedin_url'][:50]}...")

        # Display cost summary
        print(f"\n💰 COST SUMMARY")
        print("=" * 30)
        print(f"💵 Total Gemini API Cost: ${app.total_cost:.6f}")
        print(f"🔢 Total API Calls: {len(app.cost_breakdown)}")

        # Breakdown by operation
        entity_costs = [c['cost_usd'] for c in app.cost_breakdown if c['operation'] == 'entity_extraction']
        grounding_costs = [c['cost_usd'] for c in app.cost_breakdown if c['operation'] == 'grounding_search']
        company_costs = [c['cost_usd'] for c in app.cost_breakdown if c['operation'] == 'company_extraction']

        if entity_costs:
            print(f"📊 Entity Extraction: ${sum(entity_costs):.6f} ({len(entity_costs)} calls)")
        if grounding_costs:
            print(f"🔍 Company Grounding: ${sum(grounding_costs):.6f} ({len(grounding_costs)} calls)")
        if company_costs:
            print(f"🏢 Company Extraction: ${sum(company_costs):.6f} ({len(company_costs)} calls)")

        print(f"\n✅ ANALYSIS COMPLETE! Processed {len(results)} profiles successfully.")
        print("📁 Results saved to CSV files:")
        print("   • linkedin_analysis_results.csv")
        print("   • linkedin_analysis_costs.csv")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()
