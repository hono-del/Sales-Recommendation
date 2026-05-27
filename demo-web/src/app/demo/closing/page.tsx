import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { ClosingClient } from "@/components/demo/ClosingClient";

export default function ClosingPage() {
  return (
    <>
      <DemoProgressNav currentStep={7} />
      <ClosingClient />
    </>
  );
}
