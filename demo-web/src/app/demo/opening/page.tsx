import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { OpeningClient } from "@/components/demo/OpeningClient";

export default function OpeningPage() {
  return (
    <>
      <DemoProgressNav currentStep={1} />
      <OpeningClient />
    </>
  );
}
