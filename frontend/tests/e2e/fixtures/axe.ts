/** Chequeo de accesibilidad WCAG 2.2 AA con axe-core (constitución VII). */
import AxeBuilder from "@axe-core/playwright";
import { type Page, expect } from "@playwright/test";

const WCAG_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

export async function expectNoA11yViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags(WCAG_AA).analyze();
  const summary = results.violations.map(
    (violation) => `${violation.id} (${violation.impact ?? "?"}): ${violation.help}`,
  );
  expect(summary, "infracciones de accesibilidad WCAG 2.2 AA").toEqual([]);
}
