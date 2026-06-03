import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { ServiceReasoningClient } from "@/components/demo/ServiceReasoningClient";

export default function ServiceReasoningPage() {
  return (
    <>
      <DemoProgressNav currentStep={4} />
      <ServiceReasoningClient />
    </>
  );
}
