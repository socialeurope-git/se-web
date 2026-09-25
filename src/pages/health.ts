// Health check endpoint for the load balancer (official Node.js deployment guide)
export const GET = () => {
	return new Response("OK", { status: 200 });
};
