import { redirect } from "next/navigation";

/**
 * OfflineSurveillancePage has been decommissioned.
 * Dedicated navigation and entry point removed per PRD:
 * "Remove Offline Surveillance from the ROD Project".
 * Automatically redirect to Command Centre (/).
 */
export default function OfflineSurveillancePage() {
  redirect("/");
}
