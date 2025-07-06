    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with BC Bid using provided credentials."""
        try:
            logger.info("Attempting to authenticate to BC Bid...")
            
            # First navigate to the login page
            login_url = "https://www.bcbid.gov.bc.ca/page.aspx/en/ctn/links_public_browse"
            success = await self.safe_navigate(login_url)
            if not success:
                logger.error("Failed to navigate to login page")
                return False
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")
            
            # Click on "Login with a Business or Basic BCeID" link
            bceid_link = await self.page.query_selector('a[href*="logon7.gov.bc.ca"]')
            if not bceid_link:
                logger.error("Could not find BCeID login link")
                return False
            
            # Click the BCeID login link
            await bceid_link.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Wait for the login form to appear
            await self.page.wait_for_selector('input[name="user"]', timeout=10000)
            await self.page.wait_for_selector('input[name="password"]', timeout=10000)
            
            # Fill in username and password
            await self.page.fill('input[name="user"]', username)
            await self.page.fill('input[name="password"]', password)
            
            # Submit the form
            submit_button = await self.page.query_selector('input[type="submit"][name="btnSubmit"]')
            if not submit_button:
                logger.error("Could not find submit button")
                return False
            
            await submit_button.click()
            
            # Wait for navigation after login
            await self.page.wait_for_load_state("networkidle")
            
            # Check if login was successful by looking for error messages or successful redirect
            current_url = self.page.url
            
            # Check for error messages
            error_elements = await self.page.query_selector_all('.bg-error:not(.hidden)')
            if error_elements:
                error_text = await error_elements[0].text_content()
                logger.error(f"Login failed with error: {error_text}")
                return False
            
            # Check if we're still on the login page (failed login)
            if "logon7.gov.bc.ca" in current_url:
                logger.error("Still on login page after submission - authentication failed")
                return False
            
            # Check if we've been redirected to BC Bid (successful login)
            if "bcbid.gov.bc.ca" in current_url:
                logger.info("Successfully authenticated to BC Bid")
                return True
            
            logger.warning(f"Unexpected URL after login: {current_url}")
            return False
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False 