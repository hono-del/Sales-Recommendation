import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { DealerClient } from "@/components/demo/DealerClient";

export default function DealerPage() {
  return (
    <>
      <DemoProgressNav currentStep={6} />
      <DealerClient />
    </>
  );
}
