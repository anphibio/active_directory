FROM node:22-alpine

WORKDIR /app

RUN addgroup -S app && adduser -S app -G app

COPY package.json .
RUN npm install

COPY index.html .
COPY src ./src

USER app

EXPOSE 3000

CMD ["npm", "start"]
