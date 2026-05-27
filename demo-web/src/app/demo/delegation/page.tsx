import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { DelegationClient } from "@/components/demo/DelegationClient";

export default function DelegationPage() {
  return (
    <>
      <DemoProgressNav currentStep={3} />
      <DelegationClient />
    </>
  );
}
