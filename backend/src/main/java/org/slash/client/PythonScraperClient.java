package org.slash.client;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
@RegisterRestClient(configKey = "extensions-api")
@Path("/scrape")
public interface PythonScraperClient {
    @GET
    @Path("/{item}")
    public Response triggerScraper(@PathParam("item") String item);
}
