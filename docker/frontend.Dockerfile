FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Browser on the host calls the published backend, not the Docker service name.
ENV VITE_API_BASE_URL=http://127.0.0.1:8000

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
