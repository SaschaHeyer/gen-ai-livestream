# Use the official Node.js image
FROM node:14

# Create and change to the app directory
WORKDIR /usr/src/app

# Copy application dependency manifests to the container image.
# A wildcard is used to ensure both package.json AND package-lock.json are copied.
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy local code to the container image.
COPY . .

# Build Tailwind CSS
RUN npx tailwindcss build public/css/tailwind.css -o public/css/tailwind.output.css

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run the web service on container startup.
CMD [ "node", "server.js" ]
