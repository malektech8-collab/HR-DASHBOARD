import { test, expect } from '@playwright/test';

test.describe('Governance Command Center E2E Journeys', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate once
    await page.goto('/', { waitUntil: 'load' });
    // Wait for the loading spinner to disappear (handles cold start delays)
    await page.waitForSelector('text=Assembling Command Center...', { state: 'hidden', timeout: 15000 });
  });

  test('unauthorized state displays Access Denied message', async ({ page }) => {
    // Assert access is locked by default
    const deniedHeader = page.getByText('Access Denied (Fail Closed)');
    await expect(deniedHeader).toBeVisible({ timeout: 10000 });
    
    const promptText = page.getByText('Please select a valid synthetic identity');
    await expect(promptText).toBeVisible();
  });

  test('HR Analyst flow results in 403 Forbidden message', async ({ page }) => {
    // Click the HR Analyst synthetic role login button using getByRole
    const analystButton = page.getByRole('button', { name: 'HR Analyst (403)' });
    await expect(analystButton).toBeVisible({ timeout: 10000 });
    await analystButton.click();

    // Confirm that the access denied message remains, but shifts to role warning
    const deniedHeader = page.getByText('Access Denied (Fail Closed)');
    await expect(deniedHeader).toBeVisible();
    
    const roleWarning = page.getByText('HR_ANALYST role does not possess permissions');
    await expect(roleWarning).toBeVisible();
  });

  test('SYSTEM_ADMIN flow grants access and loads telemetry grid', async ({ page }) => {
    // Click the System Admin synthetic role login button using getByRole
    const adminButton = page.getByRole('button', { name: 'System Admin' });
    await expect(adminButton).toBeVisible({ timeout: 10000 });
    await adminButton.click();

    // Confirm access is granted and Gate 5 telemetry values load
    const deniedHeader = page.getByText('Access Denied (Fail Closed)');
    await expect(deniedHeader).not.toBeVisible();

    const gate5Header = page.getByText('Gate 5 Status');
    await expect(gate5Header).toBeVisible();

    const stopCriteriaHeader = page.getByText('Stop Criteria Count');
    await expect(stopCriteriaHeader).toBeVisible();
    
    const criteriaCount = page.getByText('22 Registered');
    await expect(criteriaCount).toBeVisible();
  });
});
