import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { ServiceRecommendClient } from "@/components/demo/ServiceRecommendClient";

export default function ServiceRecommendPage() {
  return (
    <>
      <DemoProgressNav currentStep={3} />
      <ServiceRecommendClient />
    </>
  );
}
