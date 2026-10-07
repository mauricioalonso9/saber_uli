/**
 * CÓDIGO GENERADO por orval desde specs/001-identidad-acceso/contracts/openapi.yaml.
 * Generado, no editar a mano: ejecute `npm run api:generate` (principio III).
 */
import type { InvitationDeliveryStatus } from "./invitationDeliveryStatus";
import type { InvitationInvitedBy } from "./invitationInvitedBy";
import type { InvitationStatus } from "./invitationStatus";

/**
 * `email` e `invitee_name` son `null` cuando el invitado fue suprimido o cuando la
 * invitación nunca aceptada superó su plazo de conservación (FR-034e).
 */
export interface Invitation {
  id: string;
  /** @nullable */
  email?: string | null;
  /** @nullable */
  invitee_name?: string | null;
  status: InvitationStatus;
  access_expires_at: string;
  link_expires_at?: string;
  /**
   * `null` si la creó el sistema (comando `invite-guest`). `display_name` es `null` si
   * quien invitó fue suprimido.
   * @nullable
   */
  invited_by: InvitationInvitedBy;
  guest_user_id?: string;
  delivery_status?: InvitationDeliveryStatus;
  /** Fecha de supresión automática si el acceso ya terminó (FR-034a) */
  retention_deletion_on?: string;
  created_at: string;
  sent_at?: string;
  accepted_at?: string;
  revoked_at?: string;
}
