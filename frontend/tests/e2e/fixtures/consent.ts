/** Pasos comunes de la autorización de datos (US2) en las pruebas e2e. */
import { type Page, expect } from "@playwright/test";

import { type MockUser, newMockUser, signInWithMicrosoft } from "./auth";
import { completeOnboarding } from "./db";

/** Elige una opción en `/bienvenida/datos` y la confirma. */
export async function decide(page: Page, option: "Acepto" | "No acepto"): Promise<void> {
  await expect(page).toHaveURL(/\/bienvenida\/datos$/);
  await page.getByRole("radio", { name: option, exact: true }).check();
  await page.getByRole("button", { name: "Confirmar mi decisión" }).click();
}

/**
 * Ingresa, acepta la política vigente y da por completado el perfil directamente en la base
 * (el formulario de perfil lo prueba `us3-first-login.spec.ts`).
 */
export async function onboardedUser(page: Page, user: MockUser = newMockUser()): Promise<MockUser> {
  await signInWithMicrosoft(page, user);
  await decide(page, "Acepto");
  await expect(page).toHaveURL(/\/bienvenida\/perfil$/);
  completeOnboarding(user.email);
  return user;
}
