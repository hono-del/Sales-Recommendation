import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { GraphClient } from "@/components/demo/GraphClient";

export default function GraphPage() {
  return (
    <>
      <DemoProgressNav currentStep={4} />
      <GraphClient />
    </>
  );
}
