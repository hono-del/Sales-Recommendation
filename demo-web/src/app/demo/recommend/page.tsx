import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { RecommendClient } from "@/components/demo/RecommendClient";

export default function RecommendPage() {
  return (
    <>
      <DemoProgressNav currentStep={5} />
      <RecommendClient />
    </>
  );
}
